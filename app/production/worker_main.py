from app.production.settings import get_settings
from app.runtime.multi_user_runtime import MultiUserRuntime
from app.production.worker import AutonomyWorker

def main():
    settings = get_settings()
    runtime = MultiUserRuntime(
        auth_database=settings.auth_database,
        token_secret=settings.auth_secret,
        token_lifetime_seconds=settings.token_lifetime_seconds,
        memory_database=settings.memory_database,
        autonomy_database=settings.autonomy_database,
    )
    worker = AutonomyWorker(runtime)
    try:
        worker.run_forever()
    finally:
        runtime.auth_repository.close()

if __name__ == "__main__":
    main()
