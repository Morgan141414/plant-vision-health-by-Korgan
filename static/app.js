const file = document.querySelector('#file');
const preview = document.querySelector('#preview');
const button = document.querySelector('#analyze');
const result = document.querySelector('#result');
file.addEventListener('change', () => {
  const selected = file.files[0]; if (!selected) return;
  preview.innerHTML = `<img alt="Выбранное растение" src="${URL.createObjectURL(selected)}">`;
  button.disabled = false; result.hidden = true;
});
button.addEventListener('click', async () => {
  button.disabled = true; button.textContent = 'Анализ...';
  const form = new FormData(); form.append('image', file.files[0]);
  try {
    const response = await fetch('/api/v1/analyze', {method: 'POST', body: form});
    const data = await response.json(); if (!response.ok) throw new Error(data.detail);
    document.querySelector('#coverage').textContent = `${data.vegetation.coverage_percent}%`;
    document.querySelector('#bbox').textContent = data.vegetation.bbox ? data.vegetation.bbox.join(', ') : 'не обнаружена';
    document.querySelector('#status').textContent = data.health.status.replace('_', ' ');
    document.querySelector('#disclaimer').textContent = data.disclaimer;
    result.hidden = false;
  } catch (error) { alert(error.message || 'Ошибка анализа'); }
  finally { button.disabled = false; button.textContent = 'Выполнить наблюдение'; }
});
