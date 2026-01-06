document.addEventListener('DOMContentLoaded', function () {
  function updatePriceFromVariantSelect(selectEl) {
    try {
      const tr = selectEl.closest('tr');
      if (!tr) return;
      const priceInput = tr.querySelector('input[name$="-price"]');
      if (!priceInput) return;
      const opt = selectEl.options[selectEl.selectedIndex];
      if (!opt) return;
      const text = opt.text || '';
      // Expect label like: "... | price=123.45"
      const match = text.match(/price\s*=\s*([0-9]+(?:\.[0-9]+)?)/i);
      if (match) {
        priceInput.value = match[1];
      }
    } catch (e) {
      // swallow
    }
  }

  // Initial bind for existing forms
  document.querySelectorAll('select[name$="-variant"]').forEach(function (el) {
    el.addEventListener('change', function () {
      updatePriceFromVariantSelect(el);
    });
    // Set price on initial load if variant is preselected
    updatePriceFromVariantSelect(el);
  });

  // When new inline forms are added dynamically
  document.addEventListener('formset:added', function (event) {
    const container = event.target;
    const sel = container.querySelector('select[name$="-variant"]');
    if (sel) {
      sel.addEventListener('change', function () {
        updatePriceFromVariantSelect(sel);
      });
      updatePriceFromVariantSelect(sel);
    }
  });
});
