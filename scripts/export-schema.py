"""导出与Alembic迁移一致的MySQL初始化SQL。"""
import subprocess
import sys
from pathlib import Path

project = Path(__file__).resolve().parents[1]
result = subprocess.run([sys.executable, '-m', 'alembic', 'upgrade', 'head', '--sql'], cwd=project / 'backend', check=True, capture_output=True, encoding='utf-8')
output = project / 'deploy/mysql/01_schema.sql'
output.write_text('USE ikeap_platform;\nSET NAMES utf8mb4;\n\n' + '\n'.join(line.rstrip() for line in result.stdout.splitlines()).rstrip() + '\n', encoding='utf-8')
print('MySQL初始化SQL已导出。')
