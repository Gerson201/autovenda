/* Comportamentos de interface: validação em tempo real, máscaras, confirmações e prévia de imagem. */
(function () {
  "use strict";

  var V = window.Validacao;

  function campoDe(elemento) {
    return elemento.closest(".campo");
  }

  function mostrarErro(elemento, mensagem) {
    var campo = campoDe(elemento);
    if (!campo) return;
    var saida = campo.querySelector(".erro-campo");
    campo.classList.toggle("campo--erro", Boolean(mensagem));
    if (mensagem) elemento.setAttribute("aria-invalid", "true");
    else elemento.removeAttribute("aria-invalid");
    if (saida) saida.textContent = mensagem || "";
  }

  function validarElemento(elemento) {
    var valor = elemento.value;
    if (elemento.type === "file") return validarArquivo(elemento);
    if (elemento.required && valor.trim() === "") return V.MENSAGENS.obrigatorio;
    if (elemento.minLength > 0 && valor.trim() !== "" && valor.trim().length < elemento.minLength) {
      return "Digite pelo menos " + elemento.minLength + " caracteres.";
    }
    var regra = elemento.dataset.regra;
    if (!regra) return null;
    var contexto = {};
    if (regra === "ano-modelo") {
      var fab = elemento.form.querySelector("[name=ano_fabricacao]");
      contexto.anoFabricacao = fab ? fab.value : undefined;
    }
    return V.validarRegra(regra, valor, contexto);
  }

  function validarArquivo(entrada) {
    var arquivo = entrada.files && entrada.files[0];
    if (!arquivo) return null;
    var maximo = Number(entrada.dataset.tamanhoMaximo || 0);
    if (maximo && arquivo.size > maximo) {
      // O limite vem do servidor (data-tamanho-maximo); a mensagem o acompanha
      // em vez de repetir "5 MB" fixo e mentir se a configuração mudar.
      return "A imagem deve ter no máximo " + Math.round(maximo / 1048576) + " MB.";
    }
    if (!/\.(jpe?g|png|webp)$/i.test(arquivo.name)) {
      return "Formato de imagem não permitido. Envie um arquivo JPG, PNG ou WEBP.";
    }
    return null;
  }

  // Pares "de/até" cujo valor inicial não pode passar do final.
  var FAIXAS = [
    { de: "preco_min", ate: "preco_max", mensagem: "O preço máximo deve ser maior que o mínimo." },
    { de: "ano_min", ate: "ano_max", mensagem: "O ano final deve ser maior que o inicial." },
  ];

  function validarFaixas(form) {
    var invalido = null;
    FAIXAS.forEach(function (faixa) {
      var de = form.querySelector("[name=" + faixa.de + "]");
      var ate = form.querySelector("[name=" + faixa.ate + "]");
      if (!de || !ate || !de.value || !ate.value) return;
      if (Number(de.value) > Number(ate.value)) {
        mostrarErro(ate, faixa.mensagem);
        invalido = invalido || ate;
      }
    });
    return invalido;
  }

  function configurarFormulario(form) {
    var campos = form.querySelectorAll("input:not([type=hidden]), select, textarea");

    campos.forEach(function (el) {
      el.addEventListener("blur", function () { mostrarErro(el, validarElemento(el)); });
      el.addEventListener("input", function () {
        if (campoDe(el) && campoDe(el).classList.contains("campo--erro")) {
          mostrarErro(el, validarElemento(el));
        }
      });
    });

    form.addEventListener("submit", function (evento) {
      var primeiroInvalido = null;
      campos.forEach(function (el) {
        var erro = validarElemento(el);
        mostrarErro(el, erro);
        if (erro && !primeiroInvalido) primeiroInvalido = el;
      });

      // Sempre avaliado, mesmo com outro campo já inválido, para que o usuário
      // veja todos os problemas de uma vez em vez de um por envio.
      var faixaInvalida = validarFaixas(form);
      primeiroInvalido = primeiroInvalido || faixaInvalida;

      if (primeiroInvalido) {
        evento.preventDefault();
        primeiroInvalido.focus();
        return;
      }

      var botao = form.querySelector("[data-confirmar-botao]");
      if (botao && !window.confirm(botao.dataset.confirmarBotao)) {
        evento.preventDefault();
        return;
      }
      // Evita envio duplicado (duplo clique).
      form.querySelectorAll("button[type=submit]").forEach(function (b) { b.disabled = true; });
    });
  }

  function configurarMascaras() {
    document.querySelectorAll("[data-mascara=telefone]").forEach(function (el) {
      el.addEventListener("input", function () { el.value = V.mascaraTelefone(el.value); });
      if (el.value) el.value = V.mascaraTelefone(el.value);
    });
    document.querySelectorAll("[data-mascara=cpf]").forEach(function (el) {
      el.addEventListener("input", function () { el.value = V.mascaraCpf(el.value); });
      if (el.value) el.value = V.mascaraCpf(el.value);
    });
    document.querySelectorAll("[data-maiusculas]").forEach(function (el) {
      el.addEventListener("input", function () { el.value = el.value.toUpperCase(); });
    });
  }

  function configurarConfirmacoes() {
    document.querySelectorAll("form[data-confirmar]").forEach(function (form) {
      form.addEventListener("submit", function (evento) {
        if (!window.confirm(form.dataset.confirmar)) evento.preventDefault();
      });
    });
  }

  function configurarPrevia() {
    document.querySelectorAll("input[type=file][data-preview]").forEach(function (entrada) {
      var imagem = document.getElementById(entrada.dataset.preview);
      entrada.addEventListener("change", function () {
        var erro = validarArquivo(entrada);
        mostrarErro(entrada, erro);
        var arquivo = entrada.files && entrada.files[0];
        if (!imagem || !arquivo || erro) return;
        imagem.src = URL.createObjectURL(arquivo);
        imagem.hidden = false;
      });
    });
  }

  function configurarContadores() {
    document.querySelectorAll("textarea[data-contador]").forEach(function (area) {
      var saida = area.parentElement.querySelector(".contador");
      function atualizar() {
        if (saida) saida.textContent = area.value.length + " de " + area.maxLength + " caracteres";
      }
      area.addEventListener("input", atualizar);
      atualizar();
    });
  }

  function configurarAlertas() {
    document.querySelectorAll(".alerta__fechar").forEach(function (botao) {
      botao.addEventListener("click", function () { botao.parentElement.remove(); });
    });
    document.querySelectorAll(".mensagens .alerta--sucesso, .mensagens .alerta--info").forEach(function (alerta) {
      setTimeout(function () { alerta.remove(); }, 6000);
    });
  }

  function configurarMenu() {
    var botao = document.querySelector(".menu__botao");
    var menu = document.getElementById("menu-principal");
    if (!botao || !menu) return;

    function definir(aberto) {
      menu.classList.toggle("aberto", aberto);
      botao.setAttribute("aria-expanded", String(aberto));
    }

    botao.addEventListener("click", function () {
      definir(!menu.classList.contains("aberto"));
    });

    // Esc fecha o menu e devolve o foco ao botão que o abriu: quem navega pelo
    // teclado ficava preso dentro do menu, sem saída a não ser percorrer todos
    // os links até o fim.
    document.addEventListener("keydown", function (evento) {
      if (evento.key !== "Escape" || !menu.classList.contains("aberto")) return;
      definir(false);
      botao.focus();
    });

    // Clicar fora também fecha, comportamento esperado em tela de celular.
    document.addEventListener("click", function (evento) {
      if (!menu.classList.contains("aberto")) return;
      if (menu.contains(evento.target) || botao.contains(evento.target)) return;
      definir(false);
    });
  }

  function configurarSenha() {
    document.querySelectorAll("[data-mostrar-senha]").forEach(function (botao) {
      var campo = document.getElementById(botao.dataset.mostrarSenha);
      botao.addEventListener("click", function () {
        var visivel = campo.type === "text";
        campo.type = visivel ? "password" : "text";
        botao.textContent = visivel ? "Mostrar" : "Ocultar";
        botao.setAttribute("aria-pressed", String(!visivel));
      });
    });
  }

  document.addEventListener("DOMContentLoaded", function () {
    document.querySelectorAll("form[data-validar]").forEach(configurarFormulario);
    configurarMascaras();
    configurarConfirmacoes();
    configurarPrevia();
    configurarContadores();
    configurarAlertas();
    configurarMenu();
    configurarSenha();
    document.querySelectorAll("[data-voltar]").forEach(function (b) {
      b.addEventListener("click", function () { history.back(); });
    });
  });
})();
