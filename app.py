import streamlit as st
import pandas as pd
import numpy as np
import os
import tempfile
from io import BytesIO
from aliasanx import Pyanx
import locale

# Configuração da página
st.set_page_config(
    page_title="Extrato → ANX",
    page_icon="📈",
    layout="wide"
)

def clean_duplicate_columns(df):
    """
    Remove colunas duplicadas adicionando sufixos numéricos.
    """
    if df is None:
        return df
    
    # Verificar se há colunas duplicadas
    if len(df.columns) != len(set(df.columns)):
        # Criar novo DataFrame com colunas únicas
        new_columns = []
        column_counts = {}
        
        for col in df.columns:
            if col in column_counts:
                column_counts[col] += 1
                new_columns.append(f"{col}_{column_counts[col]}")
            else:
                column_counts[col] = 0
                new_columns.append(col)
        
        df.columns = new_columns
        print(f"DEBUG: Colunas duplicadas renomeadas: {new_columns}")
    
    return df

def safe_dataframe_display(df, **kwargs):
    """
    Exibe um DataFrame de forma segura, lidando com colunas duplicadas.
    """
    if df is None or df.empty:
        st.info("Nenhum dado para exibir")
        return
    
    # Limpar colunas duplicadas antes de exibir
    df_clean = clean_duplicate_columns(df.copy())
    
    # Exibir o DataFrame
    st.dataframe(df_clean, **kwargs)

def safe_format_number(value):
    """
    Formata um valor numérico de forma segura, lidando com strings e valores nulos.
    """
    try:
        if pd.isna(value) or value is None:
            return "0"
        
        # Converter para float se for string
        if isinstance(value, str):
            numeric_value = to_numeric_safe(value)
        else:
            numeric_value = float(value)
        
        # Formatar com 2 casas decimais
        return f"{numeric_value:,.2f}"
    except (ValueError, TypeError):
        return "0"

def read_any_table(uploaded_file):
    """
    Lê arquivos CSV, XLS ou XLSX de forma robusta.
    Retorna DataFrame ou None em caso de erro.
    """
    try:
        file_extension = uploaded_file.name.lower().split('.')[-1]
        
        if file_extension == 'csv':
            # Tentar diferentes separadores e encodings para CSV
            separators = [None, ';', ',']
            encodings = ['utf-8-sig', 'latin1']
            
            for sep in separators:
                for encoding in encodings:
                    try:
                        uploaded_file.seek(0)  # Reset file pointer
                        df = pd.read_csv(
                            uploaded_file,
                            sep=sep,
                            encoding=encoding,
                            engine='python',
                            on_bad_lines='skip',
                            dtype=str
                        )
                        if not df.empty and len(df.columns) > 1:
                            # Limpar colunas duplicadas
                            df = clean_duplicate_columns(df)
                            return df
                    except Exception:
                        continue
            
            # Se chegou aqui, não conseguiu ler o CSV
            return None
            
        elif file_extension in ['xls', 'xlsx']:
            # Ler arquivo Excel
            uploaded_file.seek(0)
            df = pd.read_excel(uploaded_file, dtype=str)
            if not df.empty:
                # Limpar colunas duplicadas
                df = clean_duplicate_columns(df)
            return df if not df.empty else None
            
        else:
            return None
            
    except Exception as e:
        st.error(f"Erro ao ler arquivo: {str(e)}")
        return None

def to_numeric_safe(value):
    """
    Converte string para float usando padrão brasileiro.
    Substitui '.' por nada e ',' por '.', com fallback 0.0.
    """
    if pd.isna(value) or value == '' or value is None:
        return 0.0
    
    try:
        # Converter para string se não for
        str_value = str(value).strip()
        
        # Aplicar normalização brasileira
        # Remove pontos (separadores de milhares) e substitui vírgula por ponto
        normalized = str_value.replace('.', '').replace(',', '.')
        
        # Tentar converter para float
        return float(normalized)
    except (ValueError, TypeError):
        return 0.0

def format_currency_br(value):
    """Formata valor monetário no padrão brasileiro."""
    try:
        return f"R$ {value:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.')
    except:
        return f"R$ {value}"

def validate_columns(df, selected_cols):
    """Valida se as colunas selecionadas existem no DataFrame."""
    if df is None:
        return False
    
    available_cols = df.columns.tolist()
    for col in selected_cols:
        if col and col not in available_cols:
            return False
    return True

def is_numeric_column(df, col_name):
    """Verifica se uma coluna pode ser convertida para numérico."""
    if df is None or col_name not in df.columns:
        return False
    
    try:
        # Testa conversão de uma amostra
        sample = df[col_name].dropna().head(100)
        for value in sample:
            to_numeric_safe(value)
        return True
    except:
        return False

def build_anx_from_dataframe(
    df, source_col, target_col, sum_col, group_cols,
    source_desc_col=None, target_desc_col=None,
    direction_col=None, invert_when_value=None,
    output_anx_path=None, source_is_numeric=False, target_is_numeric=False,
    source_entity_type="Person", target_entity_type="Person"
):
    """
    Constrói arquivo .anx a partir do DataFrame.
    Retorna o caminho do arquivo .anx gerado.
    """
    try:
        # Fazer cópia do DataFrame para não alterar o original
        work_df = df.copy()
        
        # Normalizar colunas de origem e destino (strip espaços)
        work_df[source_col] = work_df[source_col].astype(str).str.strip()
        work_df[target_col] = work_df[target_col].astype(str).str.strip()
        
        # Debug: mostrar informações sobre os dados após normalização
        print(f"DEBUG: Dados após normalização:")
        print(f"DEBUG: {source_col} - tipo: {work_df[source_col].dtype}, valores únicos: {work_df[source_col].nunique()}")
        print(f"DEBUG: {target_col} - tipo: {work_df[target_col].dtype}, valores únicos: {work_df[target_col].nunique()}")
        print(f"DEBUG: Amostra {source_col}: {work_df[source_col].head(3).tolist()}")
        print(f"DEBUG: Amostra {target_col}: {work_df[target_col].head(3).tolist()}")
        
        # Normalizar coluna de direção se existir
        if direction_col:
            work_df[direction_col] = work_df[direction_col].astype(str).str.strip()
        
        # Converter coluna de soma para numérico (se existir)
        if sum_col:
            work_df[sum_col] = work_df[sum_col].apply(to_numeric_safe)
        else:
            # Se não há coluna de soma, criar uma coluna com valor 1
            work_df['_weight'] = 1.0
            sum_col = '_weight'
        
        # Converter origem e destino para numérico se solicitado
        # IMPORTANTE: Só converter se realmente for numérico e não contiver caracteres especiais
        if source_is_numeric:
            # Converter toda a coluna para string, limpar caracteres não numéricos
            work_df[source_col] = work_df[source_col].astype(str).str.replace('.', '').str.replace('-', '').str.replace('/', '').str.replace(' ', '')
            # Converter para numérico com tratamento de erros
            numeric_values = pd.to_numeric(work_df[source_col], errors='coerce')
            # Filtrar apenas valores válidos (não NA, não infinito)
            valid_mask = numeric_values.notna() & np.isfinite(numeric_values)
            # Criar nova coluna: valores válidos como int64, inválidos como string
            new_values = work_df[source_col].copy()
            new_values[valid_mask] = numeric_values[valid_mask].astype('int64')
            work_df[source_col] = new_values
            print(f"DEBUG: Convertida coluna {source_col} para numérico (valores inválidos mantidos como string)")
        
        if target_is_numeric:
            # Converter toda a coluna para string, limpar caracteres não numéricos
            work_df[target_col] = work_df[target_col].astype(str).str.replace('.', '').str.replace('-', '').str.replace('/', '').str.replace(' ', '')
            # Converter para numérico com tratamento de erros
            numeric_values = pd.to_numeric(work_df[target_col], errors='coerce')
            # Filtrar apenas valores válidos (não NA, não infinito)
            valid_mask = numeric_values.notna() & np.isfinite(numeric_values)
            # Criar nova coluna: valores válidos como int64, inválidos como string
            new_values = work_df[target_col].copy()
            new_values[valid_mask] = numeric_values[valid_mask].astype('int64')
            work_df[target_col] = new_values
            print(f"DEBUG: Convertida coluna {target_col} para numérico (valores inválidos mantidos como string)")
        
        # Criar mapas de descrição
        source_desc_map = {}
        target_desc_map = {}
        
        if source_desc_col:
            source_desc_map = dict(zip(
                work_df[source_col].astype(str),
                work_df[source_desc_col].astype(str)
            ))
        
        if target_desc_col:
            target_desc_map = dict(zip(
                work_df[target_col].astype(str),
                work_df[target_desc_col].astype(str)
            ))
        
        # Agrupar dados
        grouped = work_df.groupby(group_cols, as_index=False)[sum_col].sum()
        
        # Debug: mostrar informações sobre o agrupamento
        print(f"DEBUG: Dados antes do filtro: {len(grouped)} registros")
        print(f"DEBUG: Colunas no grouped: {grouped.columns.tolist()}")
        print(f"DEBUG: Primeiras linhas do grouped:")
        print(grouped.head())
        
        # Debug: verificar valores antes do filtro
        print(f"DEBUG: Valores nulos em {source_col}: {grouped[source_col].isna().sum()}")
        print(f"DEBUG: Valores nulos em {target_col}: {grouped[target_col].isna().sum()}")
        print(f"DEBUG: Valores vazios em {source_col}: {(grouped[source_col].astype(str) == '').sum()}")
        print(f"DEBUG: Valores vazios em {target_col}: {(grouped[target_col].astype(str) == '').sum()}")
        print(f"DEBUG: Self-loops: {(grouped[source_col].astype(str) == grouped[target_col].astype(str)).sum()}")
        
        # Filtrar linhas com IDs vazios ou self-loops
        original_count = len(grouped)
        
        # Debug: verificar cada condição do filtro separadamente
        print(f"DEBUG: Aplicando filtros...")
        print(f"DEBUG: Registros com {source_col} não nulo: {(grouped[source_col].notna()).sum()}")
        print(f"DEBUG: Registros com {target_col} não nulo: {(grouped[target_col].notna()).sum()}")
        print(f"DEBUG: Registros com {source_col} não vazio: {(grouped[source_col].astype(str) != '').sum()}")
        print(f"DEBUG: Registros com {target_col} não vazio: {(grouped[target_col].astype(str) != '').sum()}")
        print(f"DEBUG: Self-loops: {(grouped[source_col].astype(str) == grouped[target_col].astype(str)).sum()}")
        
        # Aplicar filtro de forma mais cuidadosa
        mask = (
            (grouped[source_col].notna()) & 
            (grouped[target_col].notna()) &
            (grouped[source_col].astype(str) != '') &
            (grouped[target_col].astype(str) != '') &
            (grouped[source_col].astype(str) != grouped[target_col].astype(str))
        )
        
        print(f"DEBUG: Máscara de filtro aplicada: {mask.sum()} registros passaram")
        
        grouped = grouped[mask]
        
        # Debug: mostrar informações após filtro
        print(f"DEBUG: Dados após filtro: {len(grouped)} registros (removidos: {original_count - len(grouped)})")
        
        if len(grouped) == 0:
            print("DEBUG: PROBLEMA - Nenhum registro restou após filtro!")
            print("DEBUG: Vamos verificar os dados originais...")
            print(f"DEBUG: Dados originais - {source_col}: {work_df[source_col].dtype}")
            print(f"DEBUG: Dados originais - {target_col}: {work_df[target_col].dtype}")
            print("DEBUG: Amostra dos dados originais:")
            print(work_df[[source_col, target_col]].head(10))
            print("DEBUG: Amostra dos dados agrupados (antes do filtro):")
            print(grouped.head(10) if len(grouped) > 0 else "Nenhum dado agrupado")
            
            # Tentar sem filtro para debug
            print("DEBUG: Tentando sem filtro para debug...")
            grouped_no_filter = work_df.groupby(group_cols, as_index=False)[sum_col].sum()
            print(f"DEBUG: Sem filtro: {len(grouped_no_filter)} registros")
            if len(grouped_no_filter) > 0:
                print("DEBUG: Primeiros registros sem filtro:")
                print(grouped_no_filter.head())
                # Usar dados sem filtro temporariamente
                grouped = grouped_no_filter
        
        # Criar instância Pyanx
        px = Pyanx()
        
        # Coletar todos os nós únicos
        all_nodes = set()
        all_nodes.update(grouped[source_col].astype(str).unique())
        all_nodes.update(grouped[target_col].astype(str).unique())
        
        # Adicionar nós
        for node_id in all_nodes:
            if node_id and node_id != 'nan':
                # Buscar descrição
                description = ""
                if node_id in source_desc_map:
                    description = source_desc_map[node_id]
                elif node_id in target_desc_map:
                    description = target_desc_map[node_id]
                
                # Determinar tipo de entidade baseado no contexto
                # Se o nó aparece como origem, usar source_entity_type
                # Se aparece apenas como destino, usar target_entity_type
                # Se aparece em ambos, usar source_entity_type como padrão
                is_source = node_id in grouped[source_col].astype(str).values
                is_target = node_id in grouped[target_col].astype(str).values
                
                if is_source:
                    entity_type = source_entity_type
                elif is_target:
                    entity_type = target_entity_type
                else:
                    entity_type = "Person"  # fallback
                
                px.add_node(
                    entity_type=entity_type,
                    label=str(node_id),
                    description=str(description) if description else ""
                )
        
        # Adicionar arestas
        for _, row in grouped.iterrows():
            source_id = str(row[source_col])
            target_id = str(row[target_col])
            value = row[sum_col]
            
            # Verificar se deve inverter direção
            should_invert = False
            if direction_col and invert_when_value:
                direction_value = str(row.get(direction_col, ''))
                should_invert = direction_value == str(invert_when_value)
            
            # Determinar origem e destino final
            if should_invert:
                final_source = target_id
                final_target = source_id
            else:
                final_source = source_id
                final_target = target_id
            
            # Criar rótulo da aresta
            if sum_col == '_weight' or value == 1.0:
                # Se não há coluna de valores ou valor é 1, usar rótulo simples
                edge_label = "1"
            else:
                edge_label = format_currency_br(value)
            
            if direction_col and direction_col in row:
                direction_value = str(row[direction_col])
                edge_label = f"{direction_value} {edge_label}"
            
            # Adicionar aresta
            px.add_edge(
                source=final_source,
                sink=final_target,
                label=edge_label
            )
        
        # Salvar arquivo .anx
        if output_anx_path:
            px.create(output_anx_path)
        
        # Criar CSV agregado
        csv_path = output_anx_path.replace('.anx', '_agregado.csv') if output_anx_path else None
        
        if csv_path:
            # Preparar DataFrame para CSV
            csv_df = grouped.copy()
            
            # Adicionar colunas de descrição se disponíveis
            if source_desc_col and source_desc_map:
                csv_df[f'{source_col}_descricao'] = csv_df[source_col].astype(str).map(source_desc_map).fillna('')
            
            if target_desc_col and target_desc_map:
                csv_df[f'{target_col}_descricao'] = csv_df[target_col].astype(str).map(target_desc_map).fillna('')
            
            # Salvar CSV
            csv_df.to_csv(csv_path, index=False, encoding='utf-8-sig')
        
        return output_anx_path
        
    except Exception as e:
        raise Exception(f"Erro na conversão para ANX: {str(e)}")

def main():
    """Função principal que monta a interface Streamlit."""
    
    st.title("📈 Extrato → ANX")
    st.markdown("Converta tabelas (CSV/XLS/XLSX) em grafos AliasAnx (.anx) e CSV agregado")
    
    # Criar abas
    tab_dados, tab_config, tab_saida = st.tabs(["Dados", "Configuração", "Saída"])
    
    # Inicializar session state
    if 'df' not in st.session_state:
        st.session_state.df = None
    if 'filename' not in st.session_state:
        st.session_state.filename = None
    
    with tab_dados:
        st.header("📁 Upload de Arquivo")
        
        uploaded_file = st.file_uploader(
            "Escolha um arquivo CSV, XLS ou XLSX",
            type=['csv', 'xls', 'xlsx'],
            help="Formatos suportados: CSV, XLS, XLSX"
        )
        
        if uploaded_file is not None:
            with st.spinner("Lendo arquivo..."):
                df = read_any_table(uploaded_file)
                
            if df is not None:
                st.session_state.df = df
                st.session_state.filename = uploaded_file.name.split('.')[0]
                
                st.success(f"✅ Arquivo carregado com sucesso! {len(df)} linhas e {len(df.columns)} colunas.")
                
                # Opção de máscara
                mask_data = st.checkbox(
                    "🔒 Mascarar dados na pré-visualização",
                    value=True,
                    help="Exibe apenas os 3 primeiros caracteres de cada valor, completando com '*'",
                    key="mask_data_input"
                )
                
                # Pré-visualização
                st.subheader("👀 Pré-visualização dos Dados")
                
                if mask_data:
                    # Criar DataFrame mascarado para exibição
                    display_df = df.head(15).copy()
                    for col in display_df.columns:
                        display_df[col] = display_df[col].astype(str).apply(
                            lambda x: x[:3] + '*' * max(0, len(x) - 3) if len(x) > 3 else x
                        )
                    safe_dataframe_display(display_df, width='stretch')
                else:
                    safe_dataframe_display(df.head(15), width='stretch')
                
                # Informações sobre as colunas
                st.subheader("📊 Informações das Colunas")
                
                # Verificar se há colunas duplicadas
                if len(df.columns) != len(set(df.columns)):
                    st.warning("⚠️ Colunas duplicadas detectadas e renomeadas automaticamente")
                    duplicate_cols = [col for col in df.columns if df.columns.tolist().count(col) > 1]
                    if duplicate_cols:
                        st.info(f"Colunas duplicadas encontradas: {duplicate_cols}")
                
                col_info = []
                for col in df.columns:
                    non_null = df[col].notna().sum()
                    is_numeric = is_numeric_column(df, col)
                    col_info.append({
                        "Coluna": col,
                        "Valores não nulos": f"{non_null}/{len(df)}",
                        "Numérica": "✅" if is_numeric else "❌"
                    })
                
                safe_dataframe_display(pd.DataFrame(col_info), width='stretch')
                
            else:
                st.error("❌ Erro ao ler o arquivo. Verifique o formato e tente novamente.")
                st.session_state.df = None
                st.session_state.filename = None
        else:
            if st.session_state.df is not None:
                st.info("📄 Arquivo carregado anteriormente ainda está disponível.")
            else:
                st.info("📤 Faça upload de um arquivo para começar.")
    
    with tab_config:
        st.header("⚙️ Configuração do Grafo")
        
        if st.session_state.df is not None:
            df = st.session_state.df
            columns = df.columns.tolist()
            
            # Configuração de origem e destino
            col1, col2 = st.columns(2)
            
            with col1:
                st.subheader("🎯 Nó de Origem")
                source_col = st.selectbox(
                    "Coluna de origem",
                    options=columns,
                    help="Identificador do nó de origem (ex.: CPF/CNPJ do Titular)"
                )
                source_is_numeric = st.checkbox(
                    "Origem é numérica (converter p/ inteiro)",
                    help="Marque se a coluna de origem contém valores numéricos"
                )
                
                source_desc_options = ["(nenhuma)"] + columns
                source_desc_col = st.selectbox(
                    "Descrição da origem (opcional)",
                    options=source_desc_options,
                    help="Coluna com descrição/nome do nó de origem"
                )
                if source_desc_col == "(nenhuma)":
                    source_desc_col = None
            
            with col2:
                st.subheader("🎯 Nó de Destino")
                
                # Filtrar colunas disponíveis para destino (excluir a coluna de origem)
                available_target_cols = [col for col in columns if col != source_col]
                if not available_target_cols:
                    available_target_cols = columns  # Fallback se todas as colunas forem iguais
                
                target_col = st.selectbox(
                    "Coluna de destino",
                    options=available_target_cols,
                    help="Identificador do nó de destino (ex.: CPF/CNPJ do Beneficiário)"
                )
                target_is_numeric = st.checkbox(
                    "Destino é numérico (converter p/ inteiro)",
                    help="Marque se a coluna de destino contém valores numéricos"
                )
                
                target_desc_options = ["(nenhuma)"] + columns
                target_desc_col = st.selectbox(
                    "Descrição do destino (opcional)",
                    options=target_desc_options,
                    help="Coluna com descrição/nome do nó de destino"
                )
                if target_desc_col == "(nenhuma)":
                    target_desc_col = None
                
                # Aviso se origem e destino são iguais
                if source_col == target_col:
                    st.warning("⚠️ Origem e destino são iguais. Isso criará self-loops que serão removidos automaticamente.")
            
            # Configuração de valor e agrupamento
            st.subheader("💰 Valor e Agrupamento")
            
            col3, col4 = st.columns(2)
            
            with col3:
                # Opção para incluir coluna de soma
                include_sum_col = st.checkbox(
                    "Incluir coluna de valores",
                    value=True,
                    help="Marque para incluir uma coluna com valores monetários"
                )
                
                if include_sum_col:
                    sum_col = st.selectbox(
                        "Coluna a somar",
                        options=columns,
                        help="Coluna com valores monetários a serem somados"
                    )
                    
                    # Validar se a coluna é numérica
                    if not is_numeric_column(df, sum_col):
                        st.warning("⚠️ A coluna selecionada pode não ser numérica. Verifique os dados.")
                else:
                    sum_col = None
                    st.info("ℹ️ Sem coluna de valores - cada aresta terá peso 1")
            
            with col4:
                # Colunas obrigatórias no agrupamento
                mandatory_cols = [source_col, target_col]
                
                group_cols = st.multiselect(
                    "Colunas de agrupamento",
                    options=columns,
                    default=mandatory_cols,
                    help="Colunas para agrupar os dados. Origem e destino são obrigatórias."
                )
                
                # Garantir que origem e destino estejam sempre incluídas
                for col in mandatory_cols:
                    if col not in group_cols:
                        group_cols.append(col)
            
            # Configuração de direção
            st.subheader("🔄 Direção da Aresta")
            
            with st.expander("Configurar direção das arestas"):
                direction_mode = st.radio(
                    "Modo de direção",
                    options=["Fixa: origem → destino", "Por coluna com inversão por valor"],
                    help="Escolha como determinar a direção das arestas"
                )
                
                direction_col = None
                invert_when_value = None
                
                if direction_mode == "Por coluna com inversão por valor":
                    direction_col = st.selectbox(
                        "Coluna de direção",
                        options=columns,
                        help="Coluna que determina a direção da aresta"
                    )
                    
                    # Obter valores únicos da coluna de direção (limitado a 50)
                    unique_values = df[direction_col].dropna().unique()[:50]
                    invert_options = ["(nenhum)"] + unique_values.tolist()
                    
                    invert_when_value = st.selectbox(
                        "Valor que inverte (faz destino → origem)",
                        options=invert_options,
                        help="Quando este valor aparecer, a direção será invertida"
                    )
                    
                    if invert_when_value == "(nenhum)":
                        invert_when_value = None
                    
                    # Incluir coluna de direção no agrupamento se não estiver
                    if direction_col and direction_col not in group_cols:
                        group_cols.append(direction_col)
                        st.info(f"ℹ️ Coluna '{direction_col}' foi adicionada ao agrupamento automaticamente.")
            
            # Salvar configurações no session state
            st.session_state.config = {
                'source_col': source_col,
                'target_col': target_col,
                'sum_col': sum_col,
                'group_cols': group_cols,
                'source_desc_col': source_desc_col,
                'target_desc_col': target_desc_col,
                'direction_col': direction_col,
                'invert_when_value': invert_when_value,
                'source_is_numeric': source_is_numeric,
                'target_is_numeric': target_is_numeric
            }
            
            # Resumo da configuração
            st.subheader("📋 Resumo da Configuração")
            config_summary = f"""
            - **Origem:** {source_col} {'(numérica)' if source_is_numeric else ''}
            - **Destino:** {target_col} {'(numérica)' if target_is_numeric else ''}
            - **Valor:** {sum_col if sum_col else 'Sem valores (peso 1)'}
            - **Agrupamento:** {', '.join(group_cols)}
            - **Direção:** {direction_mode}
            """
            
            if direction_col:
                config_summary += f"\n- **Coluna de direção:** {direction_col}"
                if invert_when_value:
                    config_summary += f"\n- **Inverte quando:** {invert_when_value}"
            
            st.markdown(config_summary)
            
            # Debug: mostrar informações sobre os dados
            st.subheader("🔍 Debug - Informações dos Dados")
            
            # Mostrar valores únicos das colunas de origem e destino
            col1, col2 = st.columns(2)
            
            with col1:
                st.write(f"**Valores únicos em {source_col}:**")
                unique_source = df[source_col].dropna().unique()[:10]  # Mostrar apenas os primeiros 10
                st.write(f"Total: {len(df[source_col].dropna().unique())} valores únicos")
                st.write(f"Primeiros: {list(unique_source)}")
            
            with col2:
                st.write(f"**Valores únicos em {target_col}:**")
                unique_target = df[target_col].dropna().unique()[:10]  # Mostrar apenas os primeiros 10
                st.write(f"Total: {len(df[target_col].dropna().unique())} valores únicos")
                st.write(f"Primeiros: {list(unique_target)}")
            
            # Mostrar algumas linhas de exemplo
            st.write("**Exemplo de dados (primeiras 5 linhas):**")
            
            # Evitar colunas duplicadas se origem e destino forem iguais
            if source_col == target_col:
                example_df = df[[source_col]].head()
                example_df.columns = [f"{source_col} (origem/destino)"]
            else:
                example_df = df[[source_col, target_col]].head()
            
            safe_dataframe_display(example_df, width='stretch')
            
            # Verificar se há self-loops (origem = destino)
            self_loops = df[df[source_col].astype(str) == df[target_col].astype(str)]
            if len(self_loops) > 0:
                st.warning(f"⚠️ Encontrados {len(self_loops)} self-loops (origem = destino) que serão removidos")
            else:
                st.success("✅ Nenhum self-loop encontrado")
            
        else:
            st.info("📤 Faça upload de um arquivo na aba 'Dados' para configurar o grafo.")
    
    with tab_saida:
        st.header("📊 Geração de Arquivos")
        
        if st.session_state.df is not None and 'config' in st.session_state:
            config = st.session_state.config
            
            # Campo para nome do arquivo
            default_name = st.session_state.filename if st.session_state.filename else "grafo"
            output_filename = st.text_input(
                "Nome do arquivo de saída",
                value=f"{default_name}.anx",
                help="Nome do arquivo .anx que será gerado"
            )
            
            # Remover extensão se o usuário digitou
            if output_filename.endswith('.anx'):
                output_filename = output_filename[:-4]
            
            # Personalização dos tipos de entidade
            st.subheader("🎨 Personalização do Grafo")
            
            col1, col2 = st.columns(2)
            
            with col1:
                source_entity_type = st.selectbox(
                    "Tipo de entidade para Coluna de Origem",
                    options=["Person", "Woman", "Phone", "Email", "Building"],
                    index=0,
                    help="Define o tipo visual da entidade de origem no grafo"
                )
            
            with col2:
                target_entity_type = st.selectbox(
                    "Tipo de entidade para Coluna de Destino",
                    options=["Person", "Woman", "Phone", "Email", "Building"],
                    index=0,
                    help="Define o tipo visual da entidade de destino no grafo"
                )
            
            # Botão para gerar
            if st.button("🚀 Gerar .anx", type="primary", width='stretch'):
                try:
                    with st.spinner("Gerando arquivos..."):
                        # Debug adicional: verificar dados antes do processamento
                        df_debug = st.session_state.df.copy()
                        
                        # Verificar se há valores nulos
                        null_source = df_debug[config['source_col']].isna().sum()
                        null_target = df_debug[config['target_col']].isna().sum()
                        if null_source > 0 or null_target > 0:
                            st.warning(f"⚠️ Debug: Valores nulos encontrados - {config['source_col']}: {null_source}, {config['target_col']}: {null_target}")
                        
                        # Verificar self-loops
                        self_loops = df_debug[df_debug[config['source_col']].astype(str) == df_debug[config['target_col']].astype(str)]
                        if len(self_loops) > 0:
                            st.warning(f"⚠️ Debug: {len(self_loops)} self-loops encontrados que serão removidos")
                        
                        # Criar diretório temporário
                        temp_dir = tempfile.mkdtemp()
                        anx_path = os.path.join(temp_dir, f"{output_filename}.anx")
                        
                        # Gerar arquivo ANX
                        result_path = build_anx_from_dataframe(
                            df=st.session_state.df,
                            source_col=config['source_col'],
                            target_col=config['target_col'],
                            sum_col=config['sum_col'],
                            group_cols=config['group_cols'],
                            source_desc_col=config['source_desc_col'],
                            target_desc_col=config['target_desc_col'],
                            direction_col=config['direction_col'],
                            invert_when_value=config['invert_when_value'],
                            output_anx_path=anx_path,
                            source_is_numeric=config['source_is_numeric'],
                            target_is_numeric=config['target_is_numeric'],
                            source_entity_type=source_entity_type,
                            target_entity_type=target_entity_type
                        )
                        
                        if result_path and os.path.exists(result_path):
                            st.success("✅ Arquivos gerados com sucesso!")
                            
                            # Salvar caminhos no session state
                            st.session_state.anx_path = result_path
                            st.session_state.csv_path = result_path.replace('.anx', '_agregado.csv')
                            
                            # Debug: verificar o CSV agregado
                            csv_path = st.session_state.csv_path
                            if os.path.exists(csv_path):
                                try:
                                    csv_df = pd.read_csv(csv_path)
                                    if len(csv_df) == 0:
                                        st.error("❌ Debug: CSV agregado está vazio! Verifique os logs no console.")
                                except Exception as e:
                                    st.error(f"❌ Debug: Erro ao ler CSV agregado: {str(e)}")
                            else:
                                st.error("❌ Debug: Arquivo CSV agregado não foi criado!")
                            
                            # Botões de download
                            col1, col2 = st.columns(2)
                            
                            with col1:
                                # Download do arquivo .anx
                                with open(result_path, 'rb') as f:
                                    st.download_button(
                                        label="📥 Baixar arquivo .anx",
                                        data=f.read(),
                                        file_name=f"{output_filename}.anx",
                                        mime="application/octet-stream",
                                        width='stretch'
                                    )
                            
                            with col2:
                                # Download do CSV agregado
                                csv_path = st.session_state.csv_path
                                if os.path.exists(csv_path):
                                    with open(csv_path, 'rb') as f:
                                        st.download_button(
                                            label="📥 Baixar CSV agregado",
                                            data=f.read(),
                                            file_name=f"{output_filename}_agregado.csv",
                                            mime="text/csv",
                                            width='stretch'
                                        )
                        else:
                            st.error("❌ Erro ao gerar os arquivos. Verifique a configuração.")
                            
                except Exception as e:
                    st.error(f"❌ Erro durante a geração: {str(e)}")
            
            # Mostrar estatísticas se já foi gerado
            if 'anx_path' in st.session_state and os.path.exists(st.session_state.anx_path):
                st.subheader("📈 Estatísticas do Grafo")
                
                # Ler CSV agregado para mostrar estatísticas
                csv_path = st.session_state.csv_path
                if os.path.exists(csv_path):
                    agg_df = pd.read_csv(csv_path)
                    
                    col1, col2, col3 = st.columns(3)
                    
                    with col1:
                        st.metric("Total de Arestas", len(agg_df))
                    
                    with col2:
                        unique_nodes = set()
                        if config['source_col'] in agg_df.columns:
                            unique_nodes.update(agg_df[config['source_col']].unique())
                        if config['target_col'] in agg_df.columns:
                            unique_nodes.update(agg_df[config['target_col']].unique())
                        st.metric("Nós Únicos", len(unique_nodes))
                    
                    with col3:
                        if config['sum_col'] and config['sum_col'] in agg_df.columns:
                            total_value = agg_df[config['sum_col']].sum()
                            st.metric("Valor Total", format_currency_br(total_value))
                        else:
                            st.metric("Total de Conexões", len(agg_df))
                    
                    # Pré-visualização do CSV agregado
                    st.subheader("👀 Pré-visualização do CSV Agregado")
                    
                    # Opção de máscara para a saída
                    mask_output_data = st.checkbox(
                        "🔒 Mascarar dados na pré-visualização",
                        value=True,
                        help="Exibe apenas os 3 primeiros caracteres de cada valor, completando com '*'",
                        key="mask_data_output"
                    )
                    
                    if mask_output_data:
                        # Criar DataFrame mascarado para exibição
                        display_agg_df = agg_df.head(10).copy()
                        for col in display_agg_df.columns:
                            display_agg_df[col] = display_agg_df[col].astype(str).apply(
                                lambda x: x[:3] + '*' * max(0, len(x) - 3) if len(x) > 3 else x
                            )
                        safe_dataframe_display(display_agg_df, width='stretch')
                    else:
                        safe_dataframe_display(agg_df.head(10), width='stretch')
        
        elif st.session_state.df is None:
            st.info("📤 Faça upload de um arquivo na aba 'Dados' para gerar os arquivos de saída.")
        else:
            st.info("⚙️ Configure o grafo na aba 'Configuração' para gerar os arquivos de saída.")
    

if __name__ == "__main__":
    main()

