import asyncio
import sys
from pathlib import Path

# Add project root to sys.path so workers can be run standalone
project_root = Path(__file__).resolve().parents[1]
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from apps.api.app.database import SessionLocal, init_db
from workers.executor import execute_scan_task


async def run_worker_loop():
    """CLI / daemon worker that continuously polls for queued scans."""
    init_db()
    print("[Vulnora Worker] Worker listening for queued security assessment jobs...")
    from apps.api.app.models import ScanModel

    while True:
        db = SessionLocal()
        try:
            queued_scan = (
                db.query(ScanModel)
                .filter(ScanModel.status == "queued")
                .order_by(ScanModel.created_at.asc())
                .first()
            )
            if queued_scan:
                scan_id = queued_scan.id
                print(f"[Vulnora Worker] Starting execution of scan: {scan_id}")
                db.close()
                await execute_scan_task(scan_id, SessionLocal)
                print(f"[Vulnora Worker] Completed scan: {scan_id}")
            else:
                db.close()
                await asyncio.sleep(2.0)
        except Exception as exc:
            db.close()
            print(f"[Vulnora Worker] Error polling queue: {exc}")
            await asyncio.sleep(3.0)


if __name__ == "__main__":
    asyncio.run(run_worker_loop())
