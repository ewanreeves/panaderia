document.addEventListener("DOMContentLoaded", () => {
  if (!document.getElementById("ticket-form")) {
    return; // turno cerrado o sin productos: no hay ticket que gestionar
  }
  const tabs = document.querySelectorAll(".tab-cat");
  const paneles = document.querySelectorAll(".grid-productos");
  const tiles = document.querySelectorAll(".tile-producto");
  const tipoBtns = document.querySelectorAll(".btn-tipo");
  const turnoBtns = document.querySelectorAll(".btn-turno");

  const fTipo = document.getElementById("f-tipo");
  const fEmpleada = document.getElementById("f-empleada");
  const fTurno = document.getElementById("f-turno");
  const fLineas = document.getElementById("f-lineas");
  const carritoEl = document.getElementById("carrito");
  const carritoVacio = document.getElementById("carrito-vacio");
  const subtotalBox = document.getElementById("carrito-subtotal");
  const subtotalValor = document.getElementById("carrito-subtotal-valor");
  const btnVaciar = document.getElementById("btn-vaciar");
  const error = document.getElementById("ticket-error");
  const form = document.getElementById("ticket-form");
  const btnImprimir = document.getElementById("btn-imprimir");

  let carrito = []; // {id, nombre, emoji, precio, cantidad}

  const euros = (v) => v.toFixed(2).replace(".", ",") + " €";

  function tileParaId(id) {
    return document.querySelector(`.tile-producto[data-id="${id}"]`);
  }

  function render() {
    // fichas: marca las que están en el carrito con su cantidad
    tiles.forEach((tile) => {
      const linea = carrito.find((l) => l.id === tile.dataset.id);
      if (linea) {
        tile.classList.add("en-carrito");
        tile.dataset.cant = linea.cantidad;
      } else {
        tile.classList.remove("en-carrito");
        delete tile.dataset.cant;
      }
    });

    // líneas del carrito
    carritoEl.querySelectorAll(".carrito-linea").forEach((el) => el.remove());
    let subtotal = 0;
    carrito.forEach((linea) => {
      const precio = parseFloat(linea.precio) || 0;
      const totalLinea = precio * linea.cantidad;
      subtotal += totalLinea;

      const div = document.createElement("div");
      div.className = "carrito-linea";
      div.dataset.id = linea.id;
      div.innerHTML = `
        <span class="carrito-emoji">${linea.emoji || ""}</span>
        <span class="carrito-nombre">${linea.nombre}</span>
        <div class="carrito-cant">
          <button type="button" class="carrito-menos" aria-label="Menos">−</button>
          <span class="carrito-cant-valor">${linea.cantidad}</span>
          <button type="button" class="carrito-mas" aria-label="Más">+</button>
        </div>
        <span class="carrito-precio">${linea.precio ? euros(totalLinea) : ""}</span>
        <button type="button" class="carrito-quitar" aria-label="Quitar">×</button>
      `;
      div.querySelector(".carrito-menos").addEventListener("click", () => cambiarCantidad(linea.id, -1));
      div.querySelector(".carrito-mas").addEventListener("click", () => cambiarCantidad(linea.id, 1));
      div.querySelector(".carrito-quitar").addEventListener("click", () => quitarLinea(linea.id));
      carritoEl.appendChild(div);
    });

    carritoVacio.hidden = carrito.length > 0;
    subtotalBox.hidden = carrito.length === 0;
    subtotalValor.textContent = euros(subtotal);
    btnVaciar.hidden = carrito.length === 0;

    fLineas.value = JSON.stringify(carrito.map((l) => ({ producto_id: l.id, cantidad: l.cantidad })));
    if (carrito.length > 0) error.hidden = true;
  }

  function agregarProducto(tile) {
    const id = tile.dataset.id;
    const existente = carrito.find((l) => l.id === id);
    if (existente) {
      existente.cantidad += 1;
    } else {
      carrito.push({
        id,
        nombre: tile.dataset.nombre,
        precio: tile.dataset.precio,
        emoji: tile.dataset.emoji,
        cantidad: 1,
      });
    }
    render();
  }

  function cambiarCantidad(id, delta) {
    const linea = carrito.find((l) => l.id === id);
    if (!linea) return;
    linea.cantidad += delta;
    if (linea.cantidad <= 0) {
      quitarLinea(id);
      return;
    }
    render();
  }

  function quitarLinea(id) {
    carrito = carrito.filter((l) => l.id !== id);
    render();
  }

  tabs.forEach((tab) => {
    tab.addEventListener("click", () => {
      tabs.forEach((t) => t.classList.remove("active"));
      tab.classList.add("active");
      const cat = tab.dataset.catTab;
      paneles.forEach((p) => {
        p.hidden = p.dataset.catPanel !== cat;
      });
    });
  });

  tiles.forEach((tile) => {
    tile.addEventListener("click", () => agregarProducto(tile));
  });

  tipoBtns.forEach((btn) => {
    btn.addEventListener("click", () => {
      tipoBtns.forEach((b) => b.classList.remove("selected"));
      btn.classList.add("selected");
      fTipo.value = btn.dataset.tipoBtn;
      error.hidden = true;
    });
  });

  turnoBtns.forEach((btn) => {
    btn.addEventListener("click", () => {
      turnoBtns.forEach((b) => b.classList.remove("selected"));
      btn.classList.add("selected");
      fTurno.value = btn.dataset.turnoBtn;
    });
  });

  // Sugiere el turno según la hora, pero se puede cambiar a mano
  if (turnoBtns.length) {
    const hora = new Date().getHours();
    const sugerido = hora < 15 ? turnoBtns[0] : turnoBtns[turnoBtns.length - 1];
    sugerido.click();
  }

  btnVaciar.addEventListener("click", () => {
    carrito = [];
    render();
  });

  if (btnImprimir) {
    btnImprimir.addEventListener("click", () => window.print());
  }

  form.addEventListener("submit", (e) => {
    if (carrito.length === 0) {
      e.preventDefault();
      error.textContent = "Añade al menos un producto al ticket";
      error.hidden = false;
      error.scrollIntoView({ behavior: "smooth", block: "center" });
      return;
    }
    if (!fTipo.value) {
      e.preventDefault();
      error.textContent = "Selecciona el tipo de movimiento (merma, reciclaje, autoconsumo o errores)";
      error.hidden = false;
      error.scrollIntoView({ behavior: "smooth", block: "center" });
      return;
    }
    if (fEmpleada && !fEmpleada.value) {
      e.preventDefault();
      error.textContent = "Selecciona quién registra el ticket — es obligatorio";
      error.hidden = false;
      fEmpleada.scrollIntoView({ behavior: "smooth", block: "center" });
    }
  });

  render();
});
