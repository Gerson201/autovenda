-- Consultas de apoio à operação e à validação do banco (PostgreSQL)

-- 1. Veículos visíveis no catálogo (regra RN03: vendidos não aparecem)
SELECT v.id, m.nome AS marca, v.modelo, v.ano_modelo, v.preco, v.status
FROM veiculo v
JOIN marca m ON m.id = v.marca_id
WHERE v.status <> 'VENDIDO'
ORDER BY v.criado_em DESC;

-- 2. Propostas pendentes com diferença em relação ao preço anunciado
SELECT p.id, c.nome AS cliente, m.nome || ' ' || v.modelo AS veiculo,
       v.preco, p.valor_ofertado, (v.preco - p.valor_ofertado) AS desconto_pedido
FROM proposta p
JOIN cliente c ON c.id = p.cliente_id
JOIN veiculo v ON v.id = p.veiculo_id
JOIN marca m   ON m.id = v.marca_id
WHERE p.status = 'PENDENTE'
ORDER BY p.criado_em;

-- 3. Faturamento por vendedor
SELECT u.nome AS vendedor, COUNT(*) AS qtd_vendas, SUM(vd.valor_final) AS total
FROM venda vd
JOIN usuario u ON u.id = vd.vendedor_id
GROUP BY u.nome
ORDER BY total DESC;

-- 4. Estoque por marca e status
SELECT m.nome, v.status, COUNT(*) AS quantidade
FROM veiculo v
JOIN marca m ON m.id = v.marca_id
GROUP BY m.nome, v.status
ORDER BY m.nome, v.status;

-- 5. Verificação de consistência: veículo VENDIDO deve ter exatamente uma venda
SELECT v.id, v.status, COUNT(vd.id) AS vendas
FROM veiculo v
LEFT JOIN venda vd ON vd.veiculo_id = v.id
GROUP BY v.id, v.status
HAVING (v.status = 'VENDIDO' AND COUNT(vd.id) <> 1)
    OR (v.status <> 'VENDIDO' AND COUNT(vd.id) > 0);
