import os
import json
import re
from datetime import datetime
from logs_manager import log, log_error
from jinja2 import Template

def parse_cucumber_json(file_paths):
    tests = []
    for filepath in file_paths:
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)
            if isinstance(data, dict):
                data = [data]
            for feature in data:
                feature_name = feature.get('name', 'Без имени фичи')
                for scenario in feature.get('elements', []):
                    if scenario.get('type') != 'scenario':
                        continue
                    scenario_name = scenario.get('name', 'Без имени сценария')
                    steps = []
                    has_failed = False
                    error_text = ""
                    for step in scenario.get('steps', []):
                        result = step.get('result', {})
                        status = result.get('status', 'unknown')
                        duration = result.get('duration', 0)
                        error = result.get('error_message', '')
                        if status == 'failed':
                            has_failed = True
                            if not error_text:
                                error_text = error
                        step_name = step.get('name', '')
                        keyword = step.get('keyword', '')
                        steps.append({
                            'text': f"{keyword} {step_name}".strip(),
                            'status': status,
                            'duration': round(duration / 1000000, 1) if duration else 0
                        })
                    total_duration = round(sum(s['duration'] for s in steps), 1)
                    status = 'failed' if has_failed else 'passed'
                    tests.append({
                        'name': f"{feature_name} → {scenario_name}",
                        'status': status,
                        'time': total_duration,
                        'error': error_text,
                        'steps': steps,
                        'tags': [tag.get('name') for tag in scenario.get('tags', [])]
                    })
        except Exception as e:
            log_error({"file": filepath, "error": str(e), "timestamp": datetime.now().isoformat()})
    return tests

def prepare_data(tests, filename=""):
    total = len(tests)
    passed = len([t for t in tests if t['status'] == 'passed'])
    failed = len([t for t in tests if t['status'] == 'failed'])
    duration = sum(t['time'] for t in tests)
    return {
        'REPORT_TITLE': f'Протокол: {filename}' if filename else 'Протокол тестирования',
        'REPORT_DATE': datetime.now().strftime('%d.%m.%Y %H:%M:%S'),
        'TOTAL_TESTS': total,
        'PASSED': passed,
        'FAILED': failed,
        'DURATION': round(duration, 1),
        'TESTS': tests
    }

REPORT_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>{{ REPORT_TITLE }}</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Arial, sans-serif; background: #f5f5f7; padding: 30px; color: #1d1d1f; }
        .container { max-width: 1200px; margin: 0 auto; background: #ffffff; border-radius: 16px; padding: 35px; }
        h1 { font-size: 26px; font-weight: 600; margin-bottom: 4px; }
        .subtitle { color: #8e8e93; font-size: 14px; margin-bottom: 25px; }
        .stats { display: flex; gap: 16px; margin-bottom: 25px; flex-wrap: wrap; }
        .stat { background: #f8f9fa; border-radius: 10px; padding: 12px 24px; text-align: center; flex: 1; min-width: 80px; }
        .stat .num { font-size: 28px; font-weight: 600; }
        .stat .label { font-size: 13px; color: #8e8e93; margin-top: 2px; }
        .stat.passed .num { color: #34c759; }
        .stat.failed .num { color: #ff3b30; }
        .stat.time .num { color: #007aff; font-size: 22px; }
        .test { background: #fafafa; border-radius: 10px; margin-bottom: 10px; padding: 16px 20px; }
        .test:hover { background: #f5f5f7; }
        .test-header { display: flex; align-items: center; gap: 14px; flex-wrap: wrap; }
        .test-status { font-size: 12px; font-weight: 600; padding: 2px 14px; border-radius: 20px; background: #e8f5e9; color: #34c759; text-transform: uppercase; }
        .test-status.failed { background: #ffebee; color: #ff3b30; }
        .test-name { font-weight: 500; font-size: 15px; flex: 1; }
        .test-time { color: #8e8e93; font-size: 13px; }
        .test-tags { display: flex; gap: 6px; flex-wrap: wrap; margin: 6px 0 8px 0; }
        .test-tag { background: #e9ecef; padding: 2px 12px; border-radius: 12px; font-size: 12px; color: #495057; }
        .step-toggle { color: #007aff; font-size: 13px; cursor: pointer; background: none; border: none; font-family: inherit; padding: 2px 0; }
        .step-toggle:hover { opacity: 0.7; }
        .steps-container { margin-top: 8px; }
        .steps-container.hidden { display: none; }
        .steps { background: #f0f0f2; border-radius: 8px; padding: 10px 14px; font-family: 'SF Mono', 'Menlo', 'Consolas', monospace; font-size: 13px; }
        .step { padding: 4px 0; display: flex; align-items: center; gap: 10px; border-bottom: 1px solid #e5e5ea; }
        .step:last-child { border-bottom: none; }
        .step-icon { min-width: 16px; }
        .step.passed .step-icon { color: #34c759; }
        .step.failed .step-icon { color: #ff3b30; }
        .step.skipped .step-icon { color: #f59e0b; }
        .step-text { flex: 1; word-break: break-word; }
        .step-duration { color: #8e8e93; font-size: 12px; }
        .error { background: #fff5f5; padding: 12px 16px; border-radius: 8px; margin-top: 8px; font-family: 'SF Mono', 'Menlo', 'Consolas', monospace; font-size: 13px; white-space: pre-wrap; color: #991b1b; }
        .error strong { color: #dc2626; }
        .arrow { display: inline-block; transition: transform 0.2s; margin-right: 4px; }
        .arrow.open { transform: rotate(90deg); }
        .footer { margin-top: 30px; padding-top: 20px; border-top: 1px solid #e9ecef; color: #8e8e93; font-size: 13px; text-align: center; }
        .hidden { display: none; }
        @media print { body { background: white; padding: 20px; } .container { box-shadow: none; border-radius: 0; padding: 20px; } .test { break-inside: avoid; } }
    </style>
    <script>
        function toggleSteps(id) {
            const container = document.getElementById('steps-' + id);
            const arrow = document.getElementById('arrow-' + id);
            if (container.classList.contains('hidden')) {
                container.classList.remove('hidden');
                arrow.classList.add('open');
            } else {
                container.classList.add('hidden');
                arrow.classList.remove('open');
            }
        }
        function downloadPDF() { window.print(); }
    </script>
</head>
<body>
<div class="container">
    <h1>{{ REPORT_TITLE }}</h1>
    <div class="subtitle">{{ REPORT_DATE }}</div>
    <div class="stats">
        <div class="stat"><div class="num">{{ TOTAL_TESTS }}</div><div class="label">Всего</div></div>
        <div class="stat passed"><div class="num">{{ PASSED }}</div><div class="label">Пройдено</div></div>
        <div class="stat failed"><div class="num">{{ FAILED }}</div><div class="label">Упало</div></div>
        <div class="stat time"><div class="num">{{ DURATION }}с</div><div class="label">Время</div></div>
    </div>
    <div style="margin-bottom: 16px;">
        <button onclick="downloadPDF()" style="padding: 8px 20px; background: #007aff; color: white; border: none; border-radius: 8px; font-size: 14px; cursor: pointer; font-family: inherit;">Сохранить PDF</button>
    </div>
    {% for test in TESTS %}
    {% set id = loop.index %}
    <div class="test">
        <div class="test-header">
            <span class="test-status {% if test.status == 'failed' %}failed{% endif %}">{{ test.status }}</span>
            <span class="test-name">{{ test.name }}</span>
            <span class="test-time">{{ test.time }}с</span>
            {% if test.steps %}
            <button class="step-toggle" onclick="toggleSteps('{{ id }}')">
                <span class="arrow open" id="arrow-{{ id }}">▶</span> Шаги ({{ test.steps|length }})
            </button>
            {% endif %}
        </div>
        {% if test.tags %}
        <div class="test-tags">
            {% for tag in test.tags %}
            <span class="test-tag">{{ tag }}</span>
            {% endfor %}
        </div>
        {% endif %}
        {% if test.steps %}
        <div class="steps-container" id="steps-{{ id }}">
            <div class="steps">
                {% for step in test.steps %}
                <div class="step {% if step.status == 'passed' %}passed{% elif step.status == 'skipped' %}skipped{% else %}failed{% endif %}">
                    <span class="step-icon">●</span>
                    <span class="step-text">{{ step.text }}</span>
                    <span class="step-duration">{{ step.duration }}мс</span>
                </div>
                {% endfor %}
            </div>
        </div>
        {% endif %}
        {% if test.status == 'failed' and test.error %}
        <div class="error"><strong>Ошибка:</strong> {{ test.error }}</div>
        {% endif %}
    </div>
    {% endfor %}
    <div class="footer">Сгенерировано автоматически</div>
</div>
</body>
</html>
"""

def get_protocols_list(reports_dir):
    protocols = []
    for filename in sorted(os.listdir(reports_dir), reverse=True):
        if filename.endswith('.html'):
            filepath = os.path.join(reports_dir, filename)
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    content = f.read()
                    total_match = re.search(r'Всего.*?(\d+)', content)
                    passed_match = re.search(r'Пройдено.*?(\d+)', content)
                    failed_match = re.search(r'Упало.*?(\d+)', content)
                    duration_match = re.search(r'Время.*?([\d.]+)с', content)
                    protocols.append({
                        'filename': filename,
                        'name': filename.replace('.html', ''),
                        'date': datetime.fromtimestamp(os.path.getmtime(filepath)).strftime('%d.%m.%Y %H:%M'),
                        'total': total_match.group(1) if total_match else '0',
                        'passed': passed_match.group(1) if passed_match else '0',
                        'failed': failed_match.group(1) if failed_match else '0',
                        'duration': duration_match.group(1) if duration_match else '0',
                        'status': 'failed' if (failed_match and int(failed_match.group(1)) > 0) else 'passed'
                    })
            except:
                pass
    return protocols