/*
 * Regras de validação do lado do cliente.
 * Funções puras (sem DOM) para poderem ser testadas no Node (tests/frontend).
 * O servidor repete todas as validações: o front-end só antecipa o feedback ao usuário.
 */
(function (raiz) {
  "use strict";

  var PLACA = /^[A-Z]{3}[0-9][A-Z0-9][0-9]{2}$/;
  var EMAIL = /^[^\s@]+@[^\s@]+\.[^\s@]{2,}$/;
  var ANO_MINIMO = 1950;

  function texto(valor) {
    return valor === null || valor === undefined ? "" : String(valor).trim();
  }

  function somenteDigitos(valor) {
    return texto(valor).replace(/\D/g, "");
  }

  function normalizarPlaca(valor) {
    return texto(valor).replace(/[^A-Za-z0-9]/g, "").toUpperCase();
  }

  function validarPlaca(valor) {
    return PLACA.test(normalizarPlaca(valor));
  }

  function validarEmail(valor) {
    return EMAIL.test(texto(valor));
  }

  function validarTelefone(valor) {
    var d = somenteDigitos(valor);
    return d.length === 10 || d.length === 11;
  }

  function validarCpf(valor) {
    var d = somenteDigitos(valor);
    if (d.length !== 11 || /^(\d)\1{10}$/.test(d)) return false;
    for (var posicao = 9; posicao <= 10; posicao++) {
      var soma = 0;
      for (var i = 0; i < posicao; i++) soma += Number(d[i]) * (posicao + 1 - i);
      var verificador = ((soma * 10) % 11) % 10;
      if (verificador !== Number(d[posicao])) return false;
    }
    return true;
  }

  function validarPositivo(valor) {
    var n = Number(texto(valor).replace(",", "."));
    return texto(valor) !== "" && isFinite(n) && n > 0;
  }

  /** Retorna a mensagem de erro, ou null se o ano de fabricação for válido. */
  function validarAnoFabricacao(ano, anoAtual) {
    var n = Number(ano);
    var limite = (anoAtual || new Date().getFullYear()) + 1;
    if (!Number.isInteger(n) || n < ANO_MINIMO || n > limite) {
      return "O ano de fabricação deve estar entre " + ANO_MINIMO + " e " + limite + ".";
    }
    return null;
  }

  /** Retorna a mensagem de erro, ou null se o ano do modelo for coerente com o de fabricação. */
  function validarAnoModelo(anoModelo, anoFabricacao) {
    if (texto(anoModelo) === "" || !Number.isInteger(Number(anoModelo))) return "Informe o ano do modelo.";
    var m = Number(anoModelo);
    var f = Number(anoFabricacao);
    if (texto(anoFabricacao) !== "" && Number.isInteger(f) && (m < f || m > f + 1)) {
      return "O ano do modelo deve ser igual ao ano de fabricação ou o ano seguinte.";
    }
    return null;
  }

  function mascaraTelefone(valor) {
    var d = somenteDigitos(valor).slice(0, 11);
    if (d.length <= 2) return d.length ? "(" + d : "";
    if (d.length <= 6) return "(" + d.slice(0, 2) + ") " + d.slice(2);
    if (d.length <= 10) return "(" + d.slice(0, 2) + ") " + d.slice(2, 6) + "-" + d.slice(6);
    return "(" + d.slice(0, 2) + ") " + d.slice(2, 7) + "-" + d.slice(7);
  }

  function mascaraCpf(valor) {
    var d = somenteDigitos(valor).slice(0, 11);
    return d
      .replace(/^(\d{3})(\d)/, "$1.$2")
      .replace(/^(\d{3})\.(\d{3})(\d)/, "$1.$2.$3")
      .replace(/\.(\d{3})(\d{1,2})$/, ".$1-$2");
  }

  function formatarMoeda(valor) {
    var n = Number(valor);
    if (!isFinite(n)) return "";
    var partes = n.toFixed(2).split(".");
    partes[0] = partes[0].replace(/\B(?=(\d{3})+(?!\d))/g, ".");
    return "R$ " + partes.join(",");
  }

  var MENSAGENS = {
    obrigatorio: "Este campo é obrigatório.",
    email: "Informe um e-mail válido (ex.: nome@dominio.com).",
    telefone: "Informe o telefone com DDD (ex.: (11) 91234-5678).",
    cpf: "CPF inválido. Confira os números digitados.",
    placa: "Placa inválida. Use o formato ABC1234 ou ABC1D23 (Mercosul).",
    positivo: "Informe um valor maior que zero.",
  };

  /** Valida um valor conforme a regra declarada em data-regra. Retorna mensagem ou null. */
  function validarRegra(regra, valor, contexto) {
    if (texto(valor) === "") return null; // obrigatoriedade é tratada à parte
    switch (regra) {
      case "email": return validarEmail(valor) ? null : MENSAGENS.email;
      case "telefone": return validarTelefone(valor) ? null : MENSAGENS.telefone;
      case "cpf": return validarCpf(valor) ? null : MENSAGENS.cpf;
      case "placa": return validarPlaca(valor) ? null : MENSAGENS.placa;
      case "positivo": return validarPositivo(valor) ? null : MENSAGENS.positivo;
      case "ano-fabricacao": return validarAnoFabricacao(valor, contexto && contexto.anoAtual);
      case "ano-modelo": return validarAnoModelo(valor, contexto && contexto.anoFabricacao);
      default: return null;
    }
  }

  var api = {
    MENSAGENS: MENSAGENS,
    normalizarPlaca: normalizarPlaca,
    validarPlaca: validarPlaca,
    validarEmail: validarEmail,
    validarTelefone: validarTelefone,
    validarCpf: validarCpf,
    validarPositivo: validarPositivo,
    validarAnoFabricacao: validarAnoFabricacao,
    validarAnoModelo: validarAnoModelo,
    validarRegra: validarRegra,
    mascaraTelefone: mascaraTelefone,
    mascaraCpf: mascaraCpf,
    formatarMoeda: formatarMoeda,
  };

  if (typeof module === "object" && module.exports) {
    module.exports = api;
  } else {
    raiz.Validacao = api;
  }
})(typeof window !== "undefined" ? window : globalThis);
