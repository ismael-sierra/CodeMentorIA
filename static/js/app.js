"use strict";

// ==========================================
// ELEMENTOS
// ==========================================

const sidebar = document.getElementById("sidebar");
const sidebarOpen = document.getElementById("sidebar-open");
const sidebarClose = document.getElementById("sidebar-close");
const sidebarOverlay = document.getElementById("sidebar-overlay");
const navButtons = document.querySelectorAll("[data-section]");
const sections = document.querySelectorAll(".workspace-section");
const sectionTitle = document.getElementById("current-section-title");
const themeButton = document.getElementById("theme-toggle");

const chatForm = document.getElementById("chat-form");
const messageInput = document.getElementById("message-input");
const chatMessages = document.getElementById("chat-messages");
const chatStatus = document.getElementById("chat-status");
const tutorIntro = document.getElementById("tutor-intro");
const newChatButton = document.getElementById("new-chat");
const sendButton = document.getElementById("send-button");
const conversationList = document.getElementById("conversation-list");
const suggestionButtons = document.querySelectorAll("[data-prompt]");

const exerciseTopic = document.getElementById("exercise-topic");
const exerciseLevel = document.getElementById("exercise-level");
const generateExerciseButton = document.getElementById("generate-exercise");
const checkSolutionButton = document.getElementById("check-solution");
const exerciseWorkspace = document.getElementById("exercise-workspace");
const exerciseDescription = document.getElementById("exercise-description");
const exerciseEmpty = document.getElementById("exercise-empty");
const codeEditor = document.getElementById("code-editor");
const exerciseFeedback = document.getElementById("exercise-feedback");

const statTotal = document.getElementById("stat-total");
const statCompleted = document.getElementById("stat-completed");
const statConversations = document.getElementById("stat-conversations");
const activityList = document.getElementById("activity-list");

// ==========================================
// ESTADO
// ==========================================

let conversacionActual = null;
let enviandoMensaje = false;
let cargandoConversacion = false;
let eliminandoConversacion = false;

let ejercicioActual = null;
let generandoEjercicio = false;
let corrigiendoEjercicio = false;
let generandoSolucion = false;
let solucionActual = null;

// ==========================================
// UTILIDADES
// ==========================================

async function solicitarJSON(url, opciones = {}) {
  const respuesta = await fetch(url, opciones);

  let datos;

  try {
    datos = await respuesta.json();
  } catch {
    throw new Error("El servidor no ha devuelto una respuesta válida.");
  }

  if (!respuesta.ok) {
    throw new Error(datos.error || "Se ha producido un error.");
  }

  return datos;
}

function crearElemento(etiqueta, texto, clase = "") {
  const elemento = document.createElement(etiqueta);
  elemento.textContent = texto;

  if (clase) {
    elemento.className = clase;
  }

  return elemento;
}

// ==========================================
// MARKDOWN Y CÓDIGO
// ==========================================

function renderizarMarkdown(texto) {
  const contenedor = document.createElement("div");
  contenedor.className = "markdown-body";

  if (typeof marked === "undefined" || typeof DOMPurify === "undefined") {
    contenedor.textContent = texto;
    return contenedor;
  }

  const html = marked.parse(texto, {
    gfm: true,
    breaks: true,
  });

  contenedor.innerHTML = DOMPurify.sanitize(html);

  contenedor.querySelectorAll("a").forEach((enlace) => {
    enlace.target = "_blank";
    enlace.rel = "noopener noreferrer";
  });

  contenedor.querySelectorAll("pre").forEach((pre) => {
    const code = pre.querySelector("code");
    if (!code) return;

    const codigoOriginal = code.textContent;
    let lenguaje = "texto";

    const claseLenguaje = Array.from(code.classList).find((clase) =>
      clase.startsWith("language-"),
    );

    if (claseLenguaje) {
      lenguaje = claseLenguaje.replace("language-", "");
    }

    if (typeof hljs !== "undefined") {
      if (hljs.getLanguage(lenguaje)) {
        code.className = `language-${lenguaje}`;
      } else {
        code.className = "";
      }

      hljs.highlightElement(code);
    }

    const bloque = document.createElement("div");
    bloque.className = "code-block";

    const cabecera = document.createElement("div");
    cabecera.className = "code-block-header";

    const etiqueta = crearElemento("span", lenguaje, "code-language");

    const boton = crearElemento("button", "Copiar", "copy-code-button");

    boton.type = "button";

    boton.addEventListener("click", async () => {
      try {
        await navigator.clipboard.writeText(codigoOriginal);
        boton.textContent = "Copiado";
      } catch {
        boton.textContent = "No se pudo copiar";
      }
    });

    boton.addEventListener("blur", () => {
      boton.textContent = "Copiar";
    });

    cabecera.append(etiqueta, boton);

    // Primero sustituir, después mover el pre.
    pre.replaceWith(bloque);
    bloque.append(cabecera, pre);
  });

  return contenedor;
}

function mostrarMarkdownSeguro(destino, texto) {
  try {
    destino.appendChild(renderizarMarkdown(texto));
  } catch (error) {
    console.error("Error mostrando Markdown:", error);
    destino.textContent = texto;
  }
}

// ==========================================
// NAVEGACIÓN
// ==========================================

const sectionNames = {
  tutor: "Tutor IA",
  ejercicios: "Ejercicios",
  progreso: "Mi progreso",
};

function mostrarSeccion(nombre) {
  if (!sectionNames[nombre]) return;

  sections.forEach((section) => {
    const activa = section.id === `section-${nombre}`;
    section.classList.toggle("active", activa);
    section.hidden = !activa;
  });

  navButtons.forEach((button) => {
    const activo = button.dataset.section === nombre;
    button.classList.toggle("active", activo);

    if (activo) {
      button.setAttribute("aria-current", "page");
    } else {
      button.removeAttribute("aria-current");
    }
  });

  sectionTitle.textContent = sectionNames[nombre];
  cerrarSidebar();

  if (nombre === "progreso") {
    cargarProgreso().catch((error) => {
      activityList.replaceChildren(crearElemento("p", error.message));
    });
  }
}

navButtons.forEach((button) => {
  button.addEventListener("click", () => {
    mostrarSeccion(button.dataset.section);
  });
});

// ==========================================
// SIDEBAR MÓVIL
// ==========================================

function abrirSidebar() {
  sidebar.classList.add("open");
  sidebarOverlay.hidden = false;
  sidebarOpen.setAttribute("aria-expanded", "true");
  sidebarClose.focus();
}

function cerrarSidebar() {
  sidebar.classList.remove("open");
  sidebarOverlay.hidden = true;
  sidebarOpen.setAttribute("aria-expanded", "false");
}

sidebarOpen.setAttribute("aria-expanded", "false");
sidebarOpen.addEventListener("click", abrirSidebar);
sidebarClose.addEventListener("click", cerrarSidebar);
sidebarOverlay.addEventListener("click", cerrarSidebar);

document.addEventListener("keydown", (event) => {
  if (event.key === "Escape" && sidebar.classList.contains("open")) {
    cerrarSidebar();
    sidebarOpen.focus();
  }
});

// ==========================================
// TEMA
// ==========================================

function aplicarTema(tema) {
  const modoClaro = tema === "light";

  document.body.classList.toggle("light", modoClaro);

  themeButton.querySelector(".nav-icon").textContent = modoClaro ? "☀" : "◐";

  themeButton.querySelector("span:last-child").textContent = modoClaro
    ? "Modo oscuro"
    : "Modo claro";

  localStorage.setItem("codementor-tema", tema);
}

aplicarTema(
  localStorage.getItem("codementor-tema") === "light" ? "light" : "dark",
);

themeButton.addEventListener("click", () => {
  const modoClaro = document.body.classList.contains("light");
  aplicarTema(modoClaro ? "dark" : "light");
});

// ==========================================
// CHAT
// ==========================================

function agregarMensaje(texto, autor) {
  const mensaje = document.createElement("div");
  mensaje.className = `message ${autor}`;

  if (autor === "assistant") {
    mostrarMarkdownSeguro(mensaje, texto);
  } else {
    mensaje.textContent = texto;
  }

  chatMessages.appendChild(mensaje);
  chatMessages.scrollTop = chatMessages.scrollHeight;
}

function actualizarBienvenida() {
  tutorIntro.hidden = chatMessages.children.length > 0;
}

chatForm.addEventListener("submit", async (event) => {
  event.preventDefault();

  if (enviandoMensaje || cargandoConversacion || eliminandoConversacion) {
    return;
  }

  const pregunta = messageInput.value.trim();

  if (!pregunta) {
    chatStatus.textContent = "Escribe una pregunta primero.";
    return;
  }

  enviandoMensaje = true;
  sendButton.disabled = true;
  chatStatus.textContent = "CodeMentor está pensando...";

  try {
    if (conversacionActual === null) {
      const nueva = await solicitarJSON("/api/conversaciones", {
        method: "POST",
      });
      conversacionActual = nueva.id;
    }

    agregarMensaje(pregunta, "user");
    actualizarBienvenida();
    messageInput.value = "";

    const datos = await solicitarJSON("/api/chat", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        mensaje: pregunta,
        conversacion_id: conversacionActual,
      }),
    });

    agregarMensaje(datos.respuesta, "assistant");
    chatStatus.textContent = "";

    try {
      await cargarListaConversaciones();
    } catch {
      chatStatus.textContent =
        "Respuesta recibida, pero no se pudo actualizar el historial.";
    }
  } catch (error) {
    chatStatus.textContent =
      error.message + " Revisa el historial antes de reenviar.";
  } finally {
    enviandoMensaje = false;
    sendButton.disabled = false;
    messageInput.focus();
  }
});

messageInput.addEventListener("keydown", (event) => {
  if (event.key === "Enter" && !event.shiftKey && !event.isComposing) {
    event.preventDefault();
    chatForm.requestSubmit();
  }
});

suggestionButtons.forEach((button) => {
  button.addEventListener("click", () => {
    messageInput.value = button.dataset.prompt;
    messageInput.focus();
    chatStatus.textContent = "";
  });
});

// ==========================================
// HISTORIAL DE CONVERSACIONES
// ==========================================

async function cargarListaConversaciones() {
  const conversaciones = await solicitarJSON("/api/conversaciones");

  conversationList.replaceChildren();

  if (conversaciones.length === 0) {
    conversationList.appendChild(
      crearElemento("p", "Aún no tienes conversaciones.", "empty-history"),
    );
    return;
  }

  conversaciones.forEach((conversacion) => {
    const fila = document.createElement("div");

    fila.style.display = "flex";
    fila.style.alignItems = "center";
    fila.style.gap = "4px";
    fila.style.width = "100%";

    const boton = crearElemento(
      "button",
      conversacion.titulo,
      "conversation-item",
    );

    boton.type = "button";
    boton.style.minWidth = "0";
    boton.style.flex = "1";

    if (conversacion.id === conversacionActual) {
      boton.classList.add("active");
    }

    boton.addEventListener("click", () => {
      abrirConversacion(conversacion.id);
    });

    // Papelera Unicode U+1F5D1
    const borrar = crearElemento("button", "\u{1F5D1}", "icon-button");

    borrar.type = "button";
    borrar.title = "Eliminar conversación";
    borrar.setAttribute(
      "aria-label",
      `Eliminar conversación: ${conversacion.titulo}`,
    );

    borrar.style.flexShrink = "0";
    borrar.style.fontSize = "17px";

    borrar.addEventListener("click", () => {
      borrarConversacion(conversacion.id, conversacion.titulo);
    });

    fila.append(boton, borrar);
    conversationList.appendChild(fila);
  });
}

// ==========================================
// ELIMINAR CONVERSACIÓN
// ==========================================

async function borrarConversacion(id, titulo) {
  if (enviandoMensaje || cargandoConversacion || eliminandoConversacion) {
    return;
  }

  const confirmado = window.confirm(
    `¿Seguro que quieres eliminar la conversación "${titulo}"?\n\n` +
      "Se borrarán todos sus mensajes y no podrás recuperarlos.",
  );

  if (!confirmado) return;

  eliminandoConversacion = true;

  try {
    await solicitarJSON(`/api/conversaciones/${id}`, { method: "DELETE" });

    if (conversacionActual === id) {
      conversacionActual = null;
      chatMessages.replaceChildren();
      messageInput.value = "";
      actualizarBienvenida();
    }

    await cargarListaConversaciones();

    chatStatus.textContent = "Conversación eliminada correctamente.";
  } catch (error) {
    chatStatus.textContent = error.message;
  } finally {
    eliminandoConversacion = false;
  }
}

async function abrirConversacion(id) {
  if (enviandoMensaje || cargandoConversacion || eliminandoConversacion) {
    return;
  }

  cargandoConversacion = true;

  try {
    const datos = await solicitarJSON(`/api/conversaciones/${id}`);

    conversacionActual = id;
    chatMessages.replaceChildren();

    datos.mensajes.forEach((mensaje) => {
      agregarMensaje(mensaje.contenido, mensaje.rol);
    });

    actualizarBienvenida();
    mostrarSeccion("tutor");
    await cargarListaConversaciones();

    chatStatus.textContent = "";
  } catch (error) {
    chatStatus.textContent = error.message;
  } finally {
    cargandoConversacion = false;
  }
}

newChatButton.addEventListener("click", async () => {
  if (enviandoMensaje || cargandoConversacion || eliminandoConversacion) {
    return;
  }

  conversacionActual = null;
  chatMessages.replaceChildren();
  messageInput.value = "";
  chatStatus.textContent = "";

  actualizarBienvenida();
  mostrarSeccion("tutor");

  try {
    await cargarListaConversaciones();
  } catch (error) {
    chatStatus.textContent = error.message;
  }

  messageInput.focus();
});

// ==========================================
// EJERCICIOS
// ==========================================

function mostrarEjercicio(ejercicio) {
  exerciseDescription.replaceChildren();

  exerciseDescription.appendChild(crearElemento("h3", ejercicio.titulo));

  exerciseDescription.appendChild(crearElemento("p", ejercicio.enunciado));

  exerciseDescription.appendChild(crearElemento("h4", "Requisitos"));

  const lista = document.createElement("ul");

  ejercicio.requisitos.forEach((requisito) => {
    lista.appendChild(crearElemento("li", requisito));
  });

  exerciseDescription.appendChild(lista);

  exerciseDescription.appendChild(crearElemento("h4", "Pista"));

  exerciseDescription.appendChild(crearElemento("p", ejercicio.pista));

  exerciseWorkspace.hidden = false;
  exerciseEmpty.hidden = true;
  exerciseFeedback.hidden = true;
  exerciseFeedback.replaceChildren();

  codeEditor.value = "";
  solucionActual = null;
}

generateExerciseButton.addEventListener("click", async () => {
  if (generandoEjercicio || corrigiendoEjercicio || generandoSolucion) {
    return;
  }

  generandoEjercicio = true;
  generateExerciseButton.disabled = true;
  generateExerciseButton.textContent = "Generando...";

  try {
    const datos = await solicitarJSON("/api/ejercicios/generar", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        tema: exerciseTopic.value,
        nivel: exerciseLevel.value,
      }),
    });

    ejercicioActual = datos.ejercicio;
    mostrarEjercicio(ejercicioActual);
  } catch (error) {
    alert(error.message);
  } finally {
    generandoEjercicio = false;
    generateExerciseButton.disabled = false;
    generateExerciseButton.textContent = "Generar ejercicio";
  }
});

// ==========================================
// CORRECCIONES
// ==========================================

function agregarListaCorreccion(contenedor, titulo, elementos) {
  contenedor.appendChild(crearElemento("h3", titulo));

  if (elementos.length === 0) {
    contenedor.appendChild(crearElemento("p", "Sin observaciones."));
    return;
  }

  const lista = document.createElement("ul");

  elementos.forEach((elemento) => {
    lista.appendChild(crearElemento("li", elemento));
  });

  contenedor.appendChild(lista);
}

function mostrarCorreccion(correccion) {
  exerciseFeedback.replaceChildren();
  exerciseFeedback.hidden = false;

  const estados = {
    correcto: "Solución aparentemente correcta",
    mejorar: "Solución con aspectos a mejorar",
    incorrecto: "Solución con errores",
  };

  exerciseFeedback.appendChild(
    crearElemento("h2", estados[correccion.estado] || "Corrección"),
  );

  exerciseFeedback.appendChild(crearElemento("p", correccion.resumen));

  agregarListaCorreccion(
    exerciseFeedback,
    "Lo que has hecho bien",
    correccion.aciertos,
  );

  agregarListaCorreccion(
    exerciseFeedback,
    "Qué puedes mejorar",
    correccion.mejoras,
  );

  exerciseFeedback.appendChild(crearElemento("h3", "Consejo de CodeMentor"));

  exerciseFeedback.appendChild(crearElemento("p", correccion.sugerencia));

  mostrarPreguntaSolucion();

  exerciseFeedback.scrollIntoView({
    behavior: "smooth",
    block: "nearest",
  });
}

// ==========================================
// PREGUNTAR SI QUIERE LA SOLUCIÓN
// ==========================================

function mostrarPreguntaSolucion() {
  const pregunta = document.createElement("div");

  pregunta.style.marginTop = "24px";
  pregunta.style.padding = "20px";
  pregunta.style.border = "1px solid var(--border-strong)";
  pregunta.style.borderRadius = "9px";
  pregunta.style.background = "var(--bg)";

  pregunta.appendChild(
    crearElemento("h3", "¿Quieres ver la solución completa?"),
  );

  pregunta.appendChild(
    crearElemento(
      "p",
      "Puedes seguir intentándolo o consultar " +
        "una solución explicada paso a paso.",
    ),
  );

  const acciones = document.createElement("div");

  acciones.style.display = "flex";
  acciones.style.flexWrap = "wrap";
  acciones.style.gap = "10px";
  acciones.style.marginTop = "16px";

  const botonSi = crearElemento(
    "button",
    "Sí, mostrar solución",
    "primary-button",
  );

  botonSi.type = "button";

  const botonNo = crearElemento(
    "button",
    "No, seguir practicando",
    "copy-code-button",
  );

  botonNo.type = "button";
  botonNo.style.padding = "11px 16px";
  botonNo.style.color = "var(--text)";
  botonNo.style.borderColor = "var(--border-strong)";

  botonSi.addEventListener("click", async () => {
    if (generandoSolucion || !ejercicioActual) return;

    botonSi.disabled = true;
    botonNo.disabled = true;
    botonSi.textContent = "Generando solución...";

    try {
      await mostrarSolucionCompleta(ejercicioActual.id, pregunta);
    } catch (error) {
      botonSi.disabled = false;
      botonNo.disabled = false;
      botonSi.textContent = "Reintentar solución";
      alert(error.message);
    }
  });

  botonNo.addEventListener("click", () => {
    pregunta.replaceChildren(
      crearElemento(
        "p",
        "Puedes mejorar tu código y volver " + "a pulsar «Corregir solución».",
      ),
    );
    codeEditor.focus();
  });

  acciones.append(botonSi, botonNo);
  pregunta.appendChild(acciones);
  exerciseFeedback.appendChild(pregunta);
}

// ==========================================
// SOLUCIÓN COMPLETA
// ==========================================

async function mostrarSolucionCompleta(id, contenedorPregunta) {
  if (generandoSolucion) return;

  generandoSolucion = true;

  try {
    let solucion;

    if (solucionActual && solucionActual.ejercicioId === id) {
      solucion = solucionActual.texto;
    } else {
      const datos = await solicitarJSON(`/api/ejercicios/${id}/solucion`, {
        method: "POST",
      });

      solucion = datos.solucion;

      solucionActual = {
        ejercicioId: id,
        texto: solucion,
      };
    }

    contenedorPregunta.replaceChildren();

    contenedorPregunta.appendChild(
      crearElemento("h3", "Solución completa explicada"),
    );

    const resultado = document.createElement("div");
    mostrarMarkdownSeguro(resultado, solucion);
    contenedorPregunta.appendChild(resultado);

    const aviso = crearElemento(
      "p",
      "Esta solución ha sido generada por IA " +
        "y no se ha ejecutado ni verificado " +
        "mediante pruebas automáticas.",
    );

    aviso.style.color = "var(--text-muted)";
    aviso.style.fontSize = "12px";

    contenedorPregunta.appendChild(aviso);

    contenedorPregunta.scrollIntoView({
      behavior: "smooth",
      block: "nearest",
    });
  } finally {
    generandoSolucion = false;
  }
}

// ==========================================
// CORREGIR SOLUCIÓN
// ==========================================

checkSolutionButton.addEventListener("click", async () => {
  if (corrigiendoEjercicio || generandoEjercicio || generandoSolucion) {
    return;
  }

  if (!ejercicioActual) {
    alert("Primero genera un ejercicio.");
    return;
  }

  const codigo = codeEditor.value.trim();

  if (!codigo) {
    alert("Escribe tu solución antes de corregir.");
    codeEditor.focus();
    return;
  }

  corrigiendoEjercicio = true;
  checkSolutionButton.disabled = true;
  checkSolutionButton.textContent = "Corrigiendo...";

  exerciseFeedback.hidden = false;
  exerciseFeedback.replaceChildren(
    crearElemento("p", "CodeMentor está revisando tu solución..."),
  );

  try {
    const datos = await solicitarJSON("/api/ejercicios/corregir", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        ejercicio_id: ejercicioActual.id,
        codigo,
      }),
    });

    mostrarCorreccion(datos.correccion);
  } catch (error) {
    exerciseFeedback.replaceChildren(crearElemento("p", error.message));
  } finally {
    corrigiendoEjercicio = false;
    checkSolutionButton.disabled = false;
    checkSolutionButton.textContent = "Corregir solución";
  }
});

// ==========================================
// RECUPERAR EJERCICIOS
// ==========================================

async function abrirEjercicioGuardado(id) {
  if (generandoEjercicio || corrigiendoEjercicio || generandoSolucion) {
    return;
  }

  try {
    const datos = await solicitarJSON(`/api/ejercicios/${id}`);

    ejercicioActual = datos.ejercicio;
    mostrarEjercicio(ejercicioActual);

    exerciseTopic.value = ejercicioActual.tema;
    exerciseLevel.value = ejercicioActual.nivel;

    if (datos.intentos.length > 0) {
      const ultimo = datos.intentos[0];
      codeEditor.value = ultimo.codigo;
      mostrarCorreccion(ultimo.correccion);
    }

    mostrarSeccion("ejercicios");

    window.scrollTo({
      top: 0,
      behavior: "smooth",
    });
  } catch (error) {
    alert(error.message);
  }
}

// ==========================================
// PROGRESO
// ==========================================

async function cargarProgreso() {
  const datos = await solicitarJSON("/api/progreso");
  const estadisticas = datos.estadisticas;

  statTotal.textContent = estadisticas.total_ejercicios;
  statCompleted.textContent = estadisticas.completados;
  statConversations.textContent = estadisticas.conversaciones;

  activityList.replaceChildren();

  if (datos.actividad.length === 0) {
    activityList.appendChild(
      crearElemento(
        "p",
        "Todavía no hay ejercicios corregidos.",
        "empty-history",
      ),
    );
    return;
  }

  const estados = {
    correcto: "Correcto",
    mejorar: "Por mejorar",
    incorrecto: "Con errores",
  };

  datos.actividad.forEach((actividad) => {
    const boton = document.createElement("button");

    boton.type = "button";
    boton.className = "conversation-item";

    boton.textContent = `${actividad.titulo} · ${estados[actividad.estado]}`;

    boton.addEventListener("click", () => {
      abrirEjercicioGuardado(actividad.ejercicio_id);
    });

    activityList.appendChild(boton);
  });
}

// ==========================================
// INICIALIZACIÓN
// ==========================================

mostrarSeccion("tutor");
actualizarBienvenida();

cargarListaConversaciones().catch((error) => {
  chatStatus.textContent = error.message;
});

console.log("CodeMentor IA inicializado.");
