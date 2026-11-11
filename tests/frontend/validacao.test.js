// Testes unitários do front-end (regras de validação e máscaras).
// Executar com: node --test tests/frontend
const { test } = require("node:test");
const assert = require("node:assert/strict");
const V = require("../../app/views/static/js/validacao.js");

test("placa: aceita formato antigo e Mercosul, com ou sem hífen", () => {
  for (const placa of ["ABC1234", "abc-1234", "ABC1D23", "abc1d23"]) {
    assert.equal(V.validarPlaca(placa), true, placa);
  }
});

test("placa: rejeita formatos inválidos", () => {
  for (const placa of ["", "AB12345", "ABCD123", "ABC12345", "1231234", null]) {
    assert.equal(V.validarPlaca(placa), false, String(placa));
  }
});

test("placa: normaliza para maiúsculas sem símbolos", () => {
  assert.equal(V.normalizarPlaca(" abc-1d23 "), "ABC1D23");
});

test("e-mail", () => {
  assert.equal(V.validarEmail("maria@exemplo.com"), true);
  assert.equal(V.validarEmail("maria@exemplo"), false);
  assert.equal(V.validarEmail("maria exemplo.com"), false);
  assert.equal(V.validarEmail(""), false);
});

test("telefone exige DDD (10 ou 11 dígitos)", () => {
  assert.equal(V.validarTelefone("(11) 98765-4321"), true);
  assert.equal(V.validarTelefone("1133334444"), true);
  assert.equal(V.validarTelefone("98765-4321"), false);
  assert.equal(V.validarTelefone("119876543210"), false);
});

test("CPF com dígitos verificadores", () => {
  assert.equal(V.validarCpf("529.982.247-25"), true);
  assert.equal(V.validarCpf("111.444.777-35"), true);
  assert.equal(V.validarCpf("529.982.247-26"), false);
  assert.equal(V.validarCpf("111.111.111-11"), false);
  assert.equal(V.validarCpf("123"), false);
});

test("valor positivo", () => {
  assert.equal(V.validarPositivo("85000"), true);
  assert.equal(V.validarPositivo("0,50"), true);
  assert.equal(V.validarPositivo("0"), false);
  assert.equal(V.validarPositivo("-1"), false);
  assert.equal(V.validarPositivo("abc"), false);
  assert.equal(V.validarPositivo(""), false);
});

test("ano de fabricação dentro do intervalo", () => {
  assert.equal(V.validarAnoFabricacao("2020", 2026), null);
  assert.equal(V.validarAnoFabricacao("2027", 2026), null);
  assert.match(V.validarAnoFabricacao("2028", 2026), /entre 1950 e 2027/);
  assert.match(V.validarAnoFabricacao("1949", 2026), /entre 1950/);
  assert.notEqual(V.validarAnoFabricacao("abc", 2026), null);
});

test("ano do modelo igual ou um ano após a fabricação", () => {
  assert.equal(V.validarAnoModelo("2021", "2021"), null);
  assert.equal(V.validarAnoModelo("2022", "2021"), null);
  assert.notEqual(V.validarAnoModelo("2023", "2021"), null);
  assert.notEqual(V.validarAnoModelo("2020", "2021"), null);
  assert.equal(V.validarAnoModelo("", "2021"), "Informe o ano do modelo.");
});

test("validarRegra ignora campo vazio (obrigatoriedade é tratada à parte)", () => {
  assert.equal(V.validarRegra("email", ""), null);
  assert.equal(V.validarRegra("email", "x"), V.MENSAGENS.email);
  assert.equal(V.validarRegra("placa", "ABC1D23"), null);
  assert.equal(V.validarRegra("regra-inexistente", "qualquer"), null);
  assert.notEqual(V.validarRegra("ano-modelo", "2030", { anoFabricacao: "2020" }), null);
});

test("máscara de telefone progressiva", () => {
  assert.equal(V.mascaraTelefone("1"), "(1");
  assert.equal(V.mascaraTelefone("119876"), "(11) 9876");
  assert.equal(V.mascaraTelefone("1133334444"), "(11) 3333-4444");
  assert.equal(V.mascaraTelefone("11987654321"), "(11) 98765-4321");
  assert.equal(V.mascaraTelefone("119876543219999"), "(11) 98765-4321");
  assert.equal(V.mascaraTelefone(""), "");
});

test("máscara de CPF", () => {
  assert.equal(V.mascaraCpf("52998224725"), "529.982.247-25");
  assert.equal(V.mascaraCpf("5299"), "529.9");
  assert.equal(V.mascaraCpf("5299822"), "529.982.2");
});

test("formatação de moeda brasileira", () => {
  assert.equal(V.formatarMoeda(85000), "R$ 85.000,00");
  assert.equal(V.formatarMoeda("1234567.8"), "R$ 1.234.567,80");
  assert.equal(V.formatarMoeda(0.5), "R$ 0,50");
  assert.equal(V.formatarMoeda("abc"), "");
});
