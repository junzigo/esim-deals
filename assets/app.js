document.querySelectorAll('[data-filter]').forEach(button => button.addEventListener('click', () => {
  document.querySelectorAll('[data-filter]').forEach(b => b.setAttribute('aria-pressed', String(b === button)));
  let shown = 0;
  document.querySelectorAll('[data-provider]').forEach(card => {card.hidden = button.dataset.filter !== 'all' && card.dataset.provider !== button.dataset.filter; if (!card.hidden) shown++;});
  document.getElementById('empty-filter').hidden = shown > 0;
}));
document.querySelectorAll('[data-code]').forEach(button => button.addEventListener('click', async () => {
  try {await navigator.clipboard.writeText(button.dataset.code); button.textContent = 'Copied ✓';}
  catch {button.textContent = 'Select the code to copy';}
}));
