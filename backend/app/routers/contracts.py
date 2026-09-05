from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.auth import get_current_vendor, require_reviewer
from app.database import get_db
from app.events import log_action, notify
from app.models import Contract, ContractMilestone, Invoice, Vendor
from app.schemas import ContractCreate, ContractMilestoneCreate, ContractMilestoneOut, ContractMilestoneUpdate, ContractOut, ContractPerformanceUpdate

router = APIRouter(prefix="/contracts", tags=["contracts"])

# Invoice statuses that count as a valid claim against the contract's
# value -- a returned/rejected invoice frees up that value again.
INVOICED_STATUSES_EXCLUDED = ("Rejected", "Returned")


def invoiced_amount(db: Session, contract_id: int) -> float:
    invoices = (
        db.query(Invoice)
        .filter(Invoice.contract_id == contract_id, Invoice.is_deleted.is_(False), ~Invoice.status.in_(INVOICED_STATUSES_EXCLUDED))
        .all()
    )
    return sum(float(i.total_amount) for i in invoices)


def _to_out(contract: Contract, db: Session) -> ContractOut:
    """Contract has no ORM relationship() to ContractMilestone (this
    project sticks to plain FK-based queries), so the milestone list is
    fetched separately and attached before serialization."""
    milestones = (
        db.query(ContractMilestone)
        .filter(ContractMilestone.contract_id == contract.id, ContractMilestone.is_deleted.is_(False))
        .order_by(ContractMilestone.due_date)
        .all()
    )
    out = ContractOut.model_validate(contract)
    out.milestones = [ContractMilestoneOut.model_validate(m) for m in milestones]
    out.remaining_value = float(contract.contract_value) - invoiced_amount(db, contract.id)
    return out


@router.get("", response_model=list[ContractOut])
def list_contracts(
    vendor: Vendor = Depends(get_current_vendor),
    db: Session = Depends(get_db),
    department: str | None = Query(default=None),
    status_filter: str | None = Query(default=None, alias="status"),
    contract_number: str | None = Query(default=None),
    valid_from: date | None = Query(default=None),
    valid_to: date | None = Query(default=None),
):
    """A reviewer sees every contract; a vendor sees only their own.
    Supports the search/filter/date-range requirements of FR-VEP-007."""
    query = db.query(Contract).filter(Contract.is_deleted.is_(False))
    if vendor.role != "reviewer":
        query = query.filter(Contract.vendor_id == vendor.id)
    if department:
        query = query.filter(Contract.department.ilike(f"%{department}%"))
    if status_filter:
        query = query.filter(Contract.status == status_filter)
    if contract_number:
        query = query.filter(Contract.contract_number.ilike(f"%{contract_number}%"))
    if valid_from:
        query = query.filter(Contract.end_date >= valid_from)
    if valid_to:
        query = query.filter(Contract.start_date <= valid_to)
    contracts = query.order_by(Contract.server_date.desc()).all()
    return [_to_out(c, db) for c in contracts]


@router.post("", response_model=ContractOut, status_code=status.HTTP_201_CREATED)
def create_contract(payload: ContractCreate, reviewer: Vendor = Depends(require_reviewer), db: Session = Depends(get_db)):
    target_vendor = db.query(Vendor).filter(Vendor.id == payload.vendor_id, Vendor.is_deleted.is_(False)).first()
    if not target_vendor:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Vendor not found")
    if target_vendor.status != "Approved":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Only an approved vendor can hold a contract")

    contract = Contract(
        vendor_id=payload.vendor_id, contract_number=payload.contract_number, po_number=payload.po_number,
        title=payload.title, description=payload.description, department=payload.department,
        currency=payload.currency, payment_terms=payload.payment_terms,
        start_date=payload.start_date, end_date=payload.end_date, contract_value=payload.contract_value,
    )
    db.add(contract)
    db.commit()
    db.refresh(contract)

    log_action(db, vendor_id=target_vendor.id, actor_id=reviewer.id, actor_role=reviewer.role, action="Contract issued", entity_type="Contract", entity_id=contract.id)
    notify(
        db, vendor_id=target_vendor.id, title="New contract issued",
        message=f"Contract {contract.contract_number} ({contract.title}) has been issued to you.", category="Contract",
    )
    db.commit()
    return _to_out(contract, db)


@router.put("/{contract_id}/performance", response_model=ContractOut)
def update_performance(contract_id: int, payload: ContractPerformanceUpdate, reviewer: Vendor = Depends(require_reviewer), db: Session = Depends(get_db)):
    contract = db.query(Contract).filter(Contract.id == contract_id, Contract.is_deleted.is_(False)).first()
    if not contract:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Contract not found")

    contract.performance_rating = payload.performance_rating
    contract.performance_remarks = payload.performance_remarks
    log_action(
        db, vendor_id=contract.vendor_id, actor_id=reviewer.id, actor_role=reviewer.role, action="Performance rated",
        entity_type="Contract", entity_id=contract.id, after_value=str(payload.performance_rating), details=payload.performance_remarks,
    )
    db.commit()
    db.refresh(contract)
    return _to_out(contract, db)


@router.post("/{contract_id}/milestones", response_model=ContractMilestoneOut, status_code=status.HTTP_201_CREATED)
def add_milestone(contract_id: int, payload: ContractMilestoneCreate, reviewer: Vendor = Depends(require_reviewer), db: Session = Depends(get_db)):
    contract = db.query(Contract).filter(Contract.id == contract_id, Contract.is_deleted.is_(False)).first()
    if not contract:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Contract not found")

    milestone = ContractMilestone(contract_id=contract_id, title=payload.title, due_date=payload.due_date, amount=payload.amount)
    db.add(milestone)
    db.commit()
    db.refresh(milestone)
    return milestone


@router.put("/milestones/{milestone_id}", response_model=ContractMilestoneOut)
def update_milestone(milestone_id: int, payload: ContractMilestoneUpdate, reviewer: Vendor = Depends(require_reviewer), db: Session = Depends(get_db)):
    if payload.status not in ("Pending", "Completed", "Delayed"):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid status")

    milestone = db.query(ContractMilestone).filter(ContractMilestone.id == milestone_id).first()
    if not milestone:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Milestone not found")

    milestone.status = payload.status
    db.commit()
    db.refresh(milestone)
    return milestone
