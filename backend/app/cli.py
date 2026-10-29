import argparse
import asyncio
from .catalog import fetch_catalog, store_catalog, seed_snapshot
from .db import SessionLocal
from .models import Audit

def main():
    parser = argparse.ArgumentParser(description='CTT Connect: mantenimiento del catálogo')
    parser.add_argument('command', choices=['sync', 'seed'])
    args = parser.parse_args()
    if args.command == 'seed':
        with SessionLocal() as db:
            count = seed_snapshot(db)
            db.commit()
        print(f'{count} fichas de respaldo importadas para revisión.')
        return
    items, errors = asyncio.run(fetch_catalog())
    with SessionLocal() as db:
        changed = store_catalog(db, items)
        db.add(Audit(actor='cli', action='catalog.sync', detail=f'{len(items)} fichas, {changed} cambios, {len(errors)} errores'))
        db.commit()
    print(f'{len(items)} fichas importadas; {changed} cambios pendientes de revisión; {len(errors)} errores.')
    for url in errors:
        print(f'No se pudo importar: {url}')

if __name__ == '__main__':
    main()
