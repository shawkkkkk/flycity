(() => {
  const copyText = async (text) => {
    if (navigator.clipboard?.writeText) {
      await navigator.clipboard.writeText(text);
      return;
    }
    const area = document.createElement('textarea');
    area.value = text;
    area.setAttribute('readonly', '');
    area.style.position = 'fixed';
    area.style.opacity = '0';
    document.body.appendChild(area);
    area.select();
    document.execCommand('copy');
    area.remove();
  };

  document.querySelectorAll('.copy-ca').forEach((button) => {
    button.addEventListener('click', async (event) => {
      event.stopPropagation();
      const ca = button.dataset.ca;
      if (!ca) return;
      const original = button.dataset.defaultLabel || button.textContent;
      try {
        await copyText(ca);
        button.textContent = 'CA COPIED';
        button.classList.add('copied');
      } catch {
        button.textContent = 'COPY FAILED';
      }
      window.setTimeout(() => {
        button.textContent = original;
        button.classList.remove('copied');
      }, 1400);
    });
  });
})();
