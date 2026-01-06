document.addEventListener("DOMContentLoaded", function () {
  function updatePriceFromVariantSelect(selectEl) {
    try {
      const tr = selectEl.closest("tr");
      if (!tr) return;
      const priceInput = tr.querySelector('input[name$="-price"]');
      if (!priceInput) return;
      const opt = selectEl.options[selectEl.selectedIndex];
      if (!opt) return;
      const dataPrice = opt.getAttribute("data-price");
      if (dataPrice) {
        priceInput.value = dataPrice;
      }
    } catch (e) {
      // swallow
    }
  }

  function populateVariants(productSelect, variantSelect) {
    const productId = productSelect.value;
    // Determine admin base (order vs cart)
    let base = "/admin/orders/order/variants/";
    if (window.location.pathname.indexOf("/admin/orders/cart/") >= 0) {
      base = "/admin/orders/cart/variants/";
    }
    // Clear current options
    while (variantSelect.options.length) {
      variantSelect.remove(0);
    }
    const blank = document.createElement("option");
    blank.value = "";
    blank.textContent = "---------";
    variantSelect.appendChild(blank);
    if (!productId) return;
    fetch(base + "?product_id=" + encodeURIComponent(productId), {
      credentials: "same-origin",
    })
      .then(function (r) {
        return r.json();
      })
      .then(function (data) {
        (data.variants || []).forEach(function (v) {
          const opt = document.createElement("option");
          opt.value = String(v.id);
          opt.textContent = v.label || "";
          if (v.price) {
            opt.setAttribute("data-price", v.price);
          }
          variantSelect.appendChild(opt);
        });
        // Reset selection and price after repopulating
        variantSelect.value = "";
        updatePriceFromVariantSelect(variantSelect);
      })
      .catch(function () {
        /* swallow */
      });
  }

  function wireRow(row) {
    const productSelect = row.querySelector('select[name$="-product"]');
    const variantSelect = row.querySelector('select[name$="-variant"]');
    if (!productSelect || !variantSelect) return;
    // On product change, repopulate variants
    productSelect.addEventListener("change", function () {
      populateVariants(productSelect, variantSelect);
    });
    // On variant change, update price
    variantSelect.addEventListener("change", function () {
      updatePriceFromVariantSelect(variantSelect);
    });
  }

  // Initial bind for existing forms
  document.querySelectorAll("tr.form-row").forEach(wireRow);

  // When new inline forms are added dynamically
  document.addEventListener("formset:added", function (event) {
    wireRow(event.target);
  });
});
