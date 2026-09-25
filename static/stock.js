document.addEventListener("DOMContentLoaded", () => {
  const buscar = document.getElementById("stock-buscar");
  const categoria = document.getElementById("stock-categoria");
  const soloContados = document.getElementById("stock-solo-contados");
  const filas = document.querySelectorAll("#stock-tabla tbody tr[data-nombre]");
  const sinResultados = document.getElementById("stock-sin-resultados");
  if (!buscar) return;

  function filtrar() {
    const texto = buscar.value.trim().toLowerCase();
    let visibles = 0;
    filas.forEach((fila) => {
      const ok =
        (!texto || fila.dataset.nombre.includes(texto)) &&
        (!categoria.value || fila.dataset.categoria === categoria.value) &&
        (!soloContados.checked || fila.dataset.contado === "1");
      fila.hidden = !ok;
      if (ok) visibles += 1;
    });
    sinResultados.hidden = visibles > 0;
  }

  buscar.addEventListener("input", filtrar);
  categoria.addEventListener("change", filtrar);
  soloContados.addEventListener("change", filtrar);

  // Enter en una casilla no debe guardar todo de golpe: pasa a la siguiente casilla visible.
  document.getElementById("stock-form").addEventListener("keydown", (e) => {
    if (e.key !== "Enter" || !e.target.classList.contains("stock-input")) return;
    e.preventDefault();
    const inputs = Array.from(document.querySelectorAll(".stock-input")).filter((i) => !i.closest("tr").hidden);
    const siguiente = inputs[inputs.indexOf(e.target) + 1];
    if (siguiente) siguiente.focus();
  });
});
