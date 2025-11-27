(function () {
  const table = document.getElementById('tabla');
  if (!table) return;

  const headers = JSON.parse(table.dataset.headers || '[]');
  const numericColumns = JSON.parse(table.dataset.numericColumns || '[]');

  const btnAgregar = document.getElementById('btnAgregar');
  const btnModificar = document.getElementById('btnModificar');
  const btnEliminar = document.getElementById('btnEliminar');
  const selectionAlert = document.getElementById('selectionAlert');
  const checkAll = document.getElementById('checkAll');

  const form = document.getElementById('formProducto');
  const btnConfirmar = document.getElementById('btnConfirmar');
  const formAlert = document.getElementById('formAlert');

  const confirmDeleteModal = new bootstrap.Modal(document.getElementById('confirmDeleteModal'));
  const deleteList = document.getElementById('deleteList');
  const btnConfirmDelete = document.getElementById('btnConfirmDelete');

  const mainModalEl = document.getElementById('modalForm');
  const btnLimpiarFiltros = document.getElementById('btnLimpiarFiltros');

  const toastEl = document.getElementById('liveToast');
  const toastBody = document.getElementById('toastBody');
  let toastInstance = null;

  let currentMode = "insert"; // 'insert' o 'update'

  function showToast(message, type) {
    if (!toastEl || !toastBody) return;

    toastEl.classList.remove('text-bg-success', 'text-bg-danger', 'text-bg-warning', 'text-bg-info');
    const cls = type === 'error' ? 'text-bg-danger' : 'text-bg-success';
    toastEl.classList.add(cls);

    toastBody.textContent = message;

    if (!toastInstance) {
      toastInstance = new bootstrap.Toast(toastEl, { delay: 2500 });
    }
    toastInstance.show();
  }

  function getCheckedRows() {
    return Array.from(table.querySelectorAll('tbody tr')).filter(tr => {
      const cb = tr.querySelector('.row-check');
      return cb && cb.checked && tr.style.display !== 'none';
    });
  }

  function getRowData(tr) {
    const cells = Array.from(tr.querySelectorAll('td'));
    const offset = 1; // checkbox
    return cells.slice(offset).map(td => td.textContent.trim());
  }

  function showSelectionHint() {
    selectionAlert.classList.remove('d-none');
    selectionAlert.classList.add('shake');
    setTimeout(() => selectionAlert.classList.remove('shake'), 400);
  }

  if (checkAll) {
    checkAll.addEventListener('change', () => {
      table.querySelectorAll('.row-check').forEach(cb => {
        if (cb.closest('tr').style.display !== 'none') {
          cb.checked = checkAll.checked;
        }
      });
    });
  }

  // --- FILTROS ---
  function readFilters() {
    const filters = {};
    headers.forEach(h => {
      if (numericColumns.includes(h)) {
        const minEl = document.getElementById(`filter_${h}_min`);
        const maxEl = document.getElementById(`filter_${h}_max`);
        const min = minEl && minEl.value !== "" ? parseFloat(minEl.value) : null;
        const max = maxEl && maxEl.value !== "" ? parseFloat(maxEl.value) : null;
        filters[h] = { type: 'num', min, max };
      } else {
        const el = document.getElementById(`filter_${h}`);
        const val = el ? el.value.trim().toLowerCase() : "";
        filters[h] = { type: 'text', value: val };
      }
    });
    return filters;
  }

  function applyFilters() {
    const filters = readFilters();
    const offset = 1; // checkbox
    const rows = table.querySelectorAll('tbody tr');

    rows.forEach(row => {
      const tds = row.querySelectorAll('td');
      let visible = true;

      headers.forEach((h, idx) => {
        const f = filters[h];
        const cellText = (tds[idx + offset]?.textContent || "").trim();
        if (f.type === 'text') {
          if (f.value && !cellText.toLowerCase().includes(f.value)) {
            visible = false;
          }
        } else {
          const num = parseFloat(cellText.replace(',', '.'));
          if (!isNaN(num)) {
            if (f.min !== null && num < f.min) visible = false;
            if (f.max !== null && num > f.max) visible = false;
          } else {
            if (f.min !== null || f.max !== null) visible = false;
          }
        }
      });

      row.style.display = visible ? "" : "none";
    });
  }

  headers.forEach(h => {
    if (numericColumns.includes(h)) {
      ['min','max'].forEach(kind => {
        const el = document.getElementById(`filter_${h}_${kind}`);
        if (el) el.addEventListener('input', applyFilters);
      });
    } else {
      const el = document.getElementById(`filter_${h}`);
      if (el) el.addEventListener('input', applyFilters);
    }
  });

  if (btnLimpiarFiltros) {
    btnLimpiarFiltros.addEventListener('click', () => {
      headers.forEach(h => {
        if (numericColumns.includes(h)) {
          ['min','max'].forEach(kind => {
            const el = document.getElementById(`filter_${h}_${kind}`);
            if (el) el.value = "";
          });
        } else {
          const el = document.getElementById(`filter_${h}`);
          if (el) el.value = "";
        }
      });
      applyFilters();
    });
  }

  // --- BOTONES CRUD ---
  btnAgregar.addEventListener('click', () => {
    currentMode = "insert";
    form.reset();
    form.classList.remove('was-validated');
    formAlert.classList.add('d-none');
  });

  btnModificar.addEventListener('click', () => {
    const rows = getCheckedRows();
    if (rows.length !== 1) {
      showSelectionHint();
      return;
    }

    currentMode = "update";

    const values = getRowData(rows[0]);
    form.reset();
    form.classList.remove('was-validated');
    formAlert.classList.add('d-none');

    headers.forEach((h, i) => {
      const input = form.querySelector(`[name="${h}"]`);
      if (!input) return;
      const v = values[i] ?? '';
      if (input.type === 'datetime-local') {
        const iso = v.replace(' ', 'T').slice(0, 16);
        input.value = iso;
      } else if (input.type === 'number') {
        input.value = v.replace(',', '.');
      } else {
        input.value = v;
      }
    });

    const formModal = new bootstrap.Modal(mainModalEl);
    formModal.show();
  });

  btnEliminar.addEventListener('click', () => {
    const rows = getCheckedRows();
    if (rows.length < 1) {
      showSelectionHint();
      return;
    }

    deleteList.innerHTML = '';
    rows.forEach(tr => {
      const data = getRowData(tr);
      const resumen = data.slice(0, Math.min(2, data.length)).join(' — ');
      const li = document.createElement('li');
      li.textContent = resumen || '(registro)';
      deleteList.appendChild(li);
    });
    confirmDeleteModal.show();
  });

  btnConfirmDelete.addEventListener('click', () => {
    const rows = getCheckedRows();
    const ids = rows.map(tr =>
      tr.querySelector('td:nth-child(2)').textContent.trim()
    );

    fetch("/productos/delete", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ ids: ids })
    })
    .then(res => res.json())
    .then(data => {
      if (data.ok) {
        confirmDeleteModal.hide();
        showToast("Productos eliminados correctamente.", "success");
        setTimeout(() => location.reload(), 800);
      } else {
        showToast(data.msg || "Error al eliminar.", "error");
      }
    })
    .catch(() => showToast("Error de comunicación con el servidor.", "error"));
  });

  btnConfirmar.addEventListener('click', (e) => {
    e.preventDefault();
    formAlert.classList.add('d-none');
    form.classList.remove('shake');

    if (!form.checkValidity()) {
      formAlert.classList.remove('d-none');
      form.classList.add('was-validated', 'shake');
      return;
    }

    // Si es update necesitamos justo UNA fila seleccionada
    let id = null;
    if (currentMode === "update") {
      const rows = getCheckedRows();
      if (rows.length !== 1) {
        showSelectionHint();
        return;
      }
      id = rows[0].querySelector('td:nth-child(2)').textContent.trim();
    }

    // Construimos el payload con los campos del formulario
    const payload = {};
    const inputs = form.querySelectorAll("input[name]");
    inputs.forEach(inp => {
      payload[inp.name] = inp.value;
    });
    if (id !== null) {
      payload.id = id;
    }

    const url = currentMode === "insert"
      ? "/productos/insert"
      : "/productos/update";

    fetch(url, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload)
    })
    .then(res => res.json())
    .then(data => {
      if (data.ok) {
        const modalInstance = bootstrap.Modal.getInstance(mainModalEl);
        if (modalInstance) modalInstance.hide();
        const msg = currentMode === "insert"
          ? "Producto agregado correctamente."
          : "Producto modificado correctamente.";
        showToast(msg, "success");
        setTimeout(() => location.reload(), 800);
      } else {
        formAlert.textContent = data.msg || "Error al guardar.";
        formAlert.classList.remove('d-none');
        showToast(data.msg || "Error al guardar.", "error");
      }
    })
    .catch(() => {
      formAlert.textContent = "Error de comunicación con el servidor.";
      formAlert.classList.remove('d-none');
      showToast("Error de comunicación con el servidor.", "error");
    });
  });

  form.querySelectorAll('input[required]').forEach(inp => {
    inp.addEventListener('blur', () => {
      if (!inp.value.trim()) inp.classList.add('is-invalid');
      else inp.classList.remove('is-invalid');
    });
  });
})();
