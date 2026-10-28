"""Package only runtime assets, including the offline aviation layer."""
from pathlib import Path
import zipfile

root = Path(__file__).resolve().parents[1]
output = root / '上海路网调色台-离线包.zip'
files = [root / p for p in ['index.html', 'style.css', 'app.js', 'README.md', 'start.command', 'start.sh', 'server.py']]
files += sorted(p for p in (root / 'vendor').rglob('*') if p.is_file() and not p.name.startswith('.'))
files += sorted((root / 'docs').glob('*.md'))
files += [root / p for p in ['AGENTS.md', 'PRODUCT.md', 'DESIGN.md']]
files += sorted((root / 'data').glob('*.json'))
files += [root / f'data/{name}.geojson.gz' for name in ['roads', 'buildings', 'landuse', 'water', 'aviation']]
files += sorted((root / 'data/tiles').rglob('*.pbf'))
with zipfile.ZipFile(output.with_suffix('.tmp'), 'w', compression=zipfile.ZIP_DEFLATED) as archive:
    for path in files:
        try:
            archive.write(path, 'shanghai_road_studio/' + path.relative_to(root).as_posix())
        except OSError as error:
            raise RuntimeError(f'Could not read {path}') from error
with zipfile.ZipFile(output.with_suffix('.tmp')) as archive:
    assert archive.testzip() is None
    assert 'shanghai_road_studio/data/aviation.geojson.gz' in archive.namelist()
output.with_suffix('.tmp').replace(output)
print(f'{len(files)} files; {output.stat().st_size} bytes; {output}')
