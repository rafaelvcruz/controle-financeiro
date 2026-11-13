-- Carga opcional das categorias iniciais. Execute somente uma vez, após criar as tabelas.
INSERT INTO categories (name, nature, suggested_percentage, active) VALUES
('Essenciais', 'DESPESA', 50.00, TRUE),
('Não-essenciais', 'DESPESA', 10.00, TRUE),
('Livre', 'DESPESA', 10.00, TRUE),
('Extra', 'MISTA', 0.00, TRUE),
('Investimentos', 'INVESTIMENTO', 30.00, TRUE)
ON CONFLICT (name) DO NOTHING;
