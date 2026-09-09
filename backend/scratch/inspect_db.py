import asyncio
from sqlalchemy import select
from app.core.database import AsyncSessionLocal
from app.models.scan import Scan
from app.models.declaration import Declaration

async def main():
    async with AsyncSessionLocal() as db:
        res = await db.execute(select(Scan).order_by(Scan.created_at.desc()).limit(5))
        scans = res.scalars().all()
        for s in scans:
            meta = s.metadata_json or {}
            print(f'SCAN {s.id}: status={s.status}, meta={meta}')
            d_res = await db.execute(select(Declaration).where(Declaration.scan_id == s.id))
            decls = d_res.scalars().all()
            for d in decls:
                print(f'   decl {d.field_type}: conf={d.confidence_score}, vdr={d.violation_detection_rate}, wf_dec={d.workflow_decision}, dec_method={d.decision_method}, human_dec={d.human_decision}, is_comp={d.is_compliant}')

if __name__ == '__main__':
    asyncio.run(main())
