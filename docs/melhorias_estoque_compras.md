# Análise Avançada & Proposta de Evolução: Módulo de Estoque e Compras

Este documento apresenta uma análise profunda do atual módulo de **Gestão de Estoque & Compras** da Naviê Vibe, comparando-o com os sistemas focados em ERPs e controle de estoque de mercado (como Totvs, Conta Azul, Opera PMS e Omie). O objetivo é identificar lacunas e propor melhorias para tornar a nossa ferramenta totalmente abrangente e de nível corporativo (Enterprise), sem que hotéis ou empresas sintam falta de nenhum recurso crítico.

---

## 1. O Cenário Atual (O que já temos)

Atualmente, o sistema possui uma base enxuta e funcional para hotéis de pequeno a médio porte:
1. **Catálogo de Produtos & Categorias**: Cadastro básico com controle de unidade de medida, código de barras e finalidade (consumo interno vs. venda/frigobar).
2. **Controle de Fornecedores**: Cadastro simples de contatos e CNPJ/CPF.
3. **Ordens de Compra Desacopladas**: Registro de compras com controle financeiro (**Pago**) e físico (**Recebido**), além de upload de arquivos anexos (comprovantes/Notas Fiscais).
4. **Sinalização de Reposição e Validade**: Alertas visuais quando o estoque está abaixo do mínimo ou quando há lotes próximos do vencimento.
5. **Auditoria Física**: Registro automático de movimentações (Entradas, Saídas, Ajustes) com referências textuais.
6. **Integração Básica**: Lançamento de despesas financeiras automáticas sob recebimento/pagamento de compras e receitas sob consumo de frigobar.

---

## 2. O que os Sistemas Enterprise possuem (As Lacunas do Nosso Modelo)

Ao analisarmos sistemas líderes de mercado focados em hotelaria (Opera PMS, Desbravador) e ERPs gerais (Totvs, Omie, Bling), identificamos as seguintes funcionalidades essenciais que empresas de maior porte exigem:

### A. Multi-almoxarifados (Sub-estoques)
* **Como funciona no mercado**: Um hotel não tem apenas um estoque único. Ele possui o **Almoxarifado Central**, a **Cozinha do Restaurante**, o **Estoque da Recepção**, os **Frigobares** (que podem ser controlados por quarto ou por andar) e o **Estoque de Enxoval/Rouparia**.
* **Limitação atual**: O modelo `Produto` tem um único campo `estoque_atual` por hotel. Não é possível saber se o refrigerante está no estoque central ou já foi transferido para o frigobar do quarto 101.

### B. Controle de Lotes Quantitativo (FIFO/FEFO)
* **Como funciona no mercado**: Quando produtos perecíveis (bebidas, amenities, alimentos) são comprados, o estoque é incrementado em lotes específicos (Lote A vence em 10 dias, Lote B vence em 60 dias). O consumo deve deduzir do lote mais próximo do vencimento (FEFO - *First Expired, First Out*).
* **Limitação atual**: O campo `validade` está no `ItemCompra`. Ao dar entrada, incrementamos um `estoque_atual` único na tabela `Produto`. Se o produto tiver 50 unidades, o sistema sabe a validade do último lote recebido, mas não sabe *quantas unidades* pertencem a cada lote específico.

### C. Valorização de Estoque & Custo Médio Ponderado (CMP)
* **Como funciona no mercado**: O preço das mercadorias flutua. Compramos Stella Artois hoje por R$ 4,00 e amanhã por R$ 4,50. A valorização do estoque contábil e o cálculo do CMV (Custo da Mercadoria Vendida) dependem do **Custo Médio Ponderado** ou de regras fiscais como PEPS (Primeiro que Entra, Primeiro que Sai / FIFO).
* **Limitação atual**: Não calculamos o custo médio. O lucro contábil é estimado pelo valor da venda menos o preço unitário do último item comprado, sem ponderação real.

### D. Processo de Suprimentos Estruturado (Workflow)
* **Como funciona no mercado**: Em empresas organizadas, uma compra passa por etapas de aprovação:
  1. **Solicitação de Compra**: A governança pede 100 sabonetes.
  2. **Cotação**: O comprador dispara pedido de cotação para 3 fornecedores.
  3. **Mapa de Coleta**: Comparativo de preços automatizado para escolher o melhor fornecedor.
  4. **Ordem de Compra**: Emissão do pedido oficial ao fornecedor vencedor.
  5. **Entrada de NF-e**: Importação do arquivo XML da Nota Fiscal Eletrônica (NF-e) que preenche e valida tudo no sistema de forma automática.
* **Limitação atual**: A compra é lançada de forma direta e manual, sem o fluxo de cotações ou importação de XML.

### E. Ficha Técnica de Alimentos & Bebidas (Receitas / Combos)
* **Como funciona no mercado**: No restaurante do hotel, ao vender uma "Caipirinha", o sistema deve deduzir do estoque: 50ml de cachaça, 1 limão e 15g de açúcar de forma automatizada. Isso é chamado de **Ficha Técnica de Produção** ou *Bill of Materials (BOM)*.
* **Limitação atual**: Apenas produtos unitários e diretos são baixados. Não há suporte a combos ou receitas de preparo.

### F. Balanço e Inventário Rotativo por Coleta
* **Como funciona no mercado**: Mensalmente, os hotéis fazem auditoria física geral (inventário). O sistema emite uma folha de contagem. O operador preenche as quantidades físicas contadas e o sistema gera relatórios de divergência, aplicando o ajuste financeiro e físico de uma única vez em lote.
* **Limitação atual**: Os ajustes são feitos item a item de forma manual no modal de movimentações.

---

## 3. Plano de Melhorias e Modelagem de Banco de Dados (Evolução Técnica)

Para levar a Naviê Vibe ao nível Enterprise, propomos a seguinte reestruturação e expansão modular:

### Melhoria 1: Multi-depósitos (Sub-estoques)
**O que fazer**: Criar o modelo `LocalArmazenamento` e transformar o saldo em uma tabela de junção `SaldoEstoqueLocal`.
* **Novo Modelo**:
  ```python
  class LocalArmazenamento(models.Model):
      hotel = models.ForeignKey(Hotel, on_delete=models.CASCADE)
      nome = models.CharField(max_length=100) # Ex: Almoxarifado Central, Copa 3º Andar
      eh_venda = models.BooleanField(default=False) # Se itens daqui geram consumo automático
      ativo = models.BooleanField(default=True)
  
  class SaldoEstoqueLocal(models.Model):
      produto = models.ForeignKey(Produto, on_delete=models.CASCADE)
      local = models.ForeignKey(LocalArmazenamento, on_delete=models.CASCADE)
      quantidade = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
      
      class Meta:
          unique_together = ('produto', 'local')
  ```
* **Impacto**: O hotel passa a rastrear exatamente onde cada insumo está fisicamente e permite transferências internas (ex: Central $\rightarrow$ Frigobar Quarto 101).

### Melhoria 2: Lotes Quantitativos e Controle de Validade (FIFO/FEFO)
**O que fazer**: Criar o controle de lotes físicos individuais vinculados a um depósito.
* **Novo Modelo**:
  ```python
  class LoteProduto(models.Model):
      produto = models.ForeignKey(Produto, on_delete=models.CASCADE)
      local = models.ForeignKey(LocalArmazenamento, on_delete=models.CASCADE)
      codigo_lote = models.CharField(max_length=50, blank=True, null=True)
      validade = models.DateField(blank=True, null=True)
      quantidade = models.DecimalField(max_digits=10, decimal_places=2)
      custo_unitario = models.DecimalField(max_digits=10, decimal_places=2)
  ```
* **Impacto**: Ao dar saída (consumo ou venda), o sistema faz uma varredura automática nos lotes daquele produto no local selecionado, ordenando por validade (`validade ASC`) e dando baixa nos lotes mais antigos primeiro (FEFO), otimizando perdas.

### Melhoria 3: Leitura de XML de Notas Fiscais (NF-e)
**O que fazer**: Implementar upload do arquivo `.xml` da Nota Fiscal Eletrônica do fornecedor.
* **Como fazer**:
  1. O usuário faz o upload do XML da NF-e.
  2. Um parser em Python lê os dados do cabeçalho (CNPJ do emitente), identifica ou cria o `Fornecedor` na base.
  3. Varre os itens da nota (tag `<det>`). Mapeia os produtos do fornecedor aos produtos existentes por código de barras ou histórico de compras.
  4. Exibe uma tela de conciliação para associar produtos novos.
  5. Cria a `Compra` automaticamente com status 'recebida', gerando os lotes e valores correspondentes.
* **Impacto**: Reduz o tempo de lançamento de compras de 15 minutos para 10 segundos, eliminando erros de digitação.

### Melhoria 4: Fichas Técnicas (CMV Dinâmico)
**O que fazer**: Permitir que produtos compostos (como drinks, refeições ou kits de higiene) tenham insumos associados.
* **Novo Modelo**:
  ```python
  class FichaTecnica(models.Model):
      produto_final = models.OneToOneField(Produto, on_delete=models.CASCADE, related_name='ficha_tecnica')
      instrucoes = models.TextField(blank=True, null=True)
  
  class ItemFichaTecnica(models.Model):
      ficha = models.ForeignKey(FichaTecnica, on_delete=models.CASCADE, related_name='ingredientes')
      insumo = models.ForeignKey(Produto, on_delete=models.CASCADE) # Ex: Vodka, Limão
      quantidade_necessaria = models.DecimalField(max_digits=10, decimal_places=2)
  ```
* **Impacto**: Na venda de um kit ou drink composto, o sistema realiza a baixa automática proporcional de todos os ingredientes que compõem o produto principal no almoxarifado correspondente.

### Melhoria 5: Inventário Geral / Balanço Físico de Estoque
**O que fazer**: Permitir abrir uma "Folha de Contagem" em lote.
* **Novo Modelo**:
  ```python
  class BalancoEstoque(models.Model):
      hotel = models.ForeignKey(Hotel, on_delete=models.CASCADE)
      local = models.ForeignKey(LocalArmazenamento, on_delete=models.CASCADE)
      status = models.CharField(choices=[('aberto', 'Contagem em Andamento'), ('finalizado', 'Processado')], default='aberto')
      criado_em = models.DateTimeField(auto_now_add=True)
  
  class ItemBalanco(models.Model):
      balanco = models.ForeignKey(BalancoEstoque, on_delete=models.CASCADE)
      produto = models.ForeignKey(Produto, on_delete=models.CASCADE)
      quantidade_esperada = models.DecimalField(max_digits=10, decimal_places=2)
      quantidade_contada = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
  ```
* **Impacto**: Ao finalizar o balanço, o sistema compara `quantidade_esperada` e `quantidade_contada`, lança as movimentações de `ajuste` com as diferenças e acerta o saldo de estoque geral.
