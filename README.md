# 📈 Extrato → ANX

Uma aplicação web desenvolvida em Streamlit para converter tabelas (CSV, XLS, XLSX) em grafos AliasAnx (.anx) e arquivos CSV agregados.

## 🎯 Funcionalidades

- **Upload de arquivos**: Suporte para CSV, XLS e XLSX
- **Configuração flexível**: Defina origem, destino, valores e agrupamentos
- **Geração de grafos**: Cria arquivos .anx compatíveis com AliasAnx
- **CSV agregado**: Gera arquivo CSV com dados consolidados
- **Interface intuitiva**: Interface web moderna e responsiva
- **Mascaramento de dados**: Opção para mascarar dados sensíveis na pré-visualização (abas Dados e Saída)
- **Validação robusta**: Tratamento de erros e validação de dados

## 🚀 Instalação

### Pré-requisitos

- Python 3.8 ou superior
- pip (gerenciador de pacotes Python)

### Passos de instalação

1. **Clone o repositório**:
   ```bash
   git clone <url-do-repositorio>
   cd PlanilhaAnx
   ```

2. **Crie um ambiente virtual** (recomendado):
   ```bash
   python -m venv venv
   
   # Windows
   venv\Scripts\activate
   
   # Linux/Mac
   source venv/bin/activate
   ```

3. **Instale as dependências**:
   ```bash
   pip install -r requirements.txt
   ```

## 🎮 Como usar

### 1. Iniciar a aplicação

```bash
streamlit run app.py
```

A aplicação será aberta automaticamente no seu navegador em `http://localhost:8501`.

### 2. Upload de dados

1. Na aba **"Dados"**, faça upload de um arquivo CSV, XLS ou XLSX
2. Visualize os dados carregados na pré-visualização
3. Verifique as informações das colunas

### 3. Configuração do grafo

Na aba **"Configuração"**:

#### Nós de Origem e Destino
- **Coluna de origem**: Identificador do nó de origem (ex.: CPF/CNPJ do Titular)
- **Coluna de destino**: Identificador do nó de destino (ex.: CPF/CNPJ do Beneficiário)
- **Opção numérica**: Marque se as colunas contêm valores numéricos
- **Descrições**: Opcionalmente, adicione colunas com descrições dos nós

#### Valor e Agrupamento
- **Coluna de valores**: Selecione uma coluna com valores monetários para somar
- **Colunas de agrupamento**: Defina como os dados serão agrupados

#### Direção das Arestas
- **Fixa**: Sempre origem → destino
- **Por coluna**: Use uma coluna para determinar a direção, com opção de inversão

### 4. Geração de arquivos

Na aba **"Saída"**:

1. Defina o nome do arquivo de saída
2. Escolha os tipos de entidade para origem e destino
3. Clique em **"Gerar .anx"**
4. Baixe os arquivos gerados:
   - Arquivo `.anx` (grafo AliasAnx)
   - Arquivo `_agregado.csv` (dados consolidados)

5. **Visualize os resultados**: Use a opção de mascaramento para proteger dados sensíveis na pré-visualização do CSV agregado

## 📊 Formatos suportados

### Arquivos de entrada
- **CSV**: Com suporte a diferentes separadores (`,`, `;`) e encodings (UTF-8, Latin1)
- **XLS**: Arquivos Excel 97-2003
- **XLSX**: Arquivos Excel modernos

### Arquivos de saída
- **`.anx`**: Formato nativo do AliasAnx para visualização de grafos
- **`_agregado.csv`**: Dados consolidados em formato CSV

## ⚙️ Configurações avançadas

### Tipos de entidade
- **Person**: Pessoa (padrão)
- **Woman**: Mulher
- **Phone**: Telefone
- **Email**: E-mail
- **Building**: Edifício/Organização

### Tratamento de dados
- **Colunas duplicadas**: Renomeadas automaticamente com sufixos numéricos
- **Valores nulos**: Filtrados automaticamente
- **Self-loops**: Removidos automaticamente (origem = destino)
- **Formatação brasileira**: Suporte para valores monetários no padrão brasileiro
- **Mascaramento de dados**: Proteção de dados sensíveis nas pré-visualizações (mostra apenas 3 primeiros caracteres)

## 🔧 Dependências principais

- **Streamlit**: Framework web para Python
- **Pandas**: Manipulação de dados
- **AliasAnx**: Biblioteca para criação de grafos
- **NumPy**: Computação numérica

## 📝 Exemplo de uso

1. **Dados de entrada** (CSV):
   ```csv
   Titular,Beneficiario,Valor,Tipo
   12345678901,98765432109,1000.50,Transferencia
   12345678901,11122233344,500.00,Pagamento
   ```

2. **Configuração**:
   - Origem: `Titular`
   - Destino: `Beneficiario`
   - Valor: `Valor`
   - Agrupamento: `Titular`, `Beneficiario`

3. **Resultado**:
   - Grafo com nós representando CPFs
   - Arestas com valores das transações
   - CSV agregado com totais por par origem-destino

## 🐛 Solução de problemas

### Erro ao ler arquivo
- Verifique se o arquivo está em um formato suportado
- Para CSV, tente diferentes separadores (`,`, `;`)
- Verifique a codificação do arquivo

### Nenhum dado após filtro
- Verifique se as colunas de origem e destino não estão vazias
- Confirme se não há apenas self-loops nos dados
- Verifique se os valores nas colunas são válidos

### Problemas de encoding
- Para arquivos CSV com caracteres especiais, use UTF-8
- Se necessário, converta o arquivo para UTF-8 antes do upload

## 📄 Licença

Este projeto está sob a licença MIT. Veja o arquivo LICENSE para mais detalhes.

Desenvolvido por Cristiano Ritta