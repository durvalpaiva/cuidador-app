import streamlit as st
import pandas as pd
from datetime import time
from dotenv import load_dotenv
import os
from supabase import create_client

load_dotenv()
supabase_url = os.getenv("SUPABASE_URL")
supabase_key = os.getenv("SUPABASE_KEY")
supabase = create_client(supabase_url, supabase_key)

# --- Inicializa flags ---
if "token_processado" not in st.session_state:
    st.session_state["token_processado"] = False
if "usuario" not in st.session_state:
    st.session_state["usuario"] = None

# --- Campo oculto para receber o token via JS ---
token_input = st.text_input("token", key="token_input", label_visibility="visible")
st.markdown("""
<style>
input[aria-label="token"] {
  visibility: hidden;
  height: 0px;
}
</style>
""", unsafe_allow_html=True)

import streamlit.components.v1 as components
components.html("""
<script>
  const fragment = window.location.hash;
  if (fragment.includes("access_token")) {
    const params = new URLSearchParams(fragment.slice(1));
    const token = params.get("access_token");
    if (token) {
      // Redireciona para a mesma página, mas com o token como parâmetro na URL
      window.location.href = window.location.pathname + "?token=" + token;
    }
  }
</script>
""", height=0)

# --- DEBUG ---
st.write("DEBUG:", dict(st.session_state))

# Captura o token da query string
params = st.query_params
token = params.get("token", [None])[0] if "token" in params else None

if token and not st.session_state.get("token_processado", False):
    try:
        session = supabase.auth.set_session(token, "")
        st.session_state["access_token"] = token
        st.session_state["usuario"] = session.user
        st.session_state["token_processado"] = True
        st.query_params.clear()  # Limpa a query string
        st.experimental_rerun()
    except Exception as e:
        st.error(f"Erro ao autenticar com token: {e}")
        st.stop()

# ✅ Processa o token se ainda não foi processado
if st.session_state["token_input"] and not st.session_state["token_processado"]:
    try:
        session = supabase.auth.set_session(st.session_state["token_input"], "")
        st.session_state["access_token"] = st.session_state["token_input"]
        st.session_state["usuario"] = session.user
        st.session_state["token_processado"] = True
        st.experimental_rerun()
    except Exception as e:
        st.error(f"Erro ao autenticar com token: {e}")
        st.stop()

# ✅ Se ainda não processou o token, aguarde
if not st.session_state["token_processado"] and st.session_state["token_input"]:
    st.info("🔄 Processando login...")
    st.stop()

# --- Função de login ---
def login_page():
    st.title("🔐 Login no Sistema de Cuidados")
    tipo_login = st.radio("Escolha o método de login:", ["E-mail e senha", "Google", "Facebook"])
    if tipo_login == "E-mail e senha":
        email = st.text_input("E-mail")
        senha = st.text_input("Senha", type="password")
        if st.button("Entrar"):
            try:
                result = supabase.auth.sign_in_with_password({"email": email, "password": senha})
                st.session_state["usuario"] = result.user
                st.session_state["token_processado"] = True  # <-- Adicione isso!
                st.success("✅ Login realizado com sucesso!")
                st.experimental_rerun()
            except Exception as e:
                st.error("Erro ao fazer login: " + str(e))
    elif tipo_login == "Google":
        st.markdown(
            "[🔗 Entrar com Google](https://dmatpfeiqddnfauxlhoh.supabase.co/auth/v1/authorize?provider=google&redirect_to=http://localhost:8501)",
            unsafe_allow_html=True
        )
    elif tipo_login == "Facebook":
        st.markdown(
            "[🔗 Entrar com Facebook](https://dmatpfeiqddnfauxlhoh.supabase.co/auth/v1/authorize?provider=facebook&redirect_to=http://localhost:8501)",
            unsafe_allow_html=True
        )

# ✅ Verificação de login
if st.session_state["usuario"] is None:
    login_page()
    st.stop()


# 🩺 Título principal
st.title("🩺 Sistema de Cuidados - Protótipo")

# 🔗 Carregando dados reais das tabelas Supabase
def carregar_tabela(nome):
    try:
        response = supabase.table(nome).select("*").execute()
        return pd.DataFrame(response.data)
    except Exception as e:
        st.error(f"Erro ao carregar '{nome}': {e}")
        return pd.DataFrame()

df_registros = carregar_tabela("registros_diarios")
if not df_registros.empty and "data" in df_registros.columns:
    df_registros["data"] = pd.to_datetime(df_registros["data"]).dt.strftime("%d/%m/%Y")

df_cuidadores = carregar_tabela("cuidadores")
df_medicamentos = carregar_tabela("medicamentos")
df_alimentacao = carregar_tabela("alimentacao")

# 🔍 Sidebar para filtros de registros
st.sidebar.title("🔍 Filtros de Registros Diários Quadro Geral")

if df_registros.empty:
    st.sidebar.warning("⚠️ Nenhum dado encontrado na tabela 'registros_diarios'.")
else:
    colunas_registros = list(df_registros.columns)

    colunas_selecionadas = st.sidebar.multiselect(
        "🔽 Colunas visíveis:",
        colunas_registros,
        default=colunas_registros,
        key="multiselect_colunas_visiveis"
    )

    col1, col2 = st.sidebar.columns(2)

    col_filtro = col1.selectbox(
        "🎯 Filtrar por:",
        [c for c in colunas_registros if c != 'id'],
        key="selectbox_filtro_coluna"
    )

    valor_filtro = col2.selectbox(
        "🧮 Valor:",
        df_registros[col_filtro].unique(),
        key="selectbox_valor_filtro"
    )

# ADICIONE ESTES BOTÕES:
    status_filtrar = col1.button("🔍 Filtrar", key="btn_filtrar")
    status_limpar = col2.button("🔹 Limpar", key="btn_limpar")

abas = st.tabs(["📋 Registros Diários", "🧑‍⚕️ Cuidadores", "💊 Medicamentos", "🍽️ Alimentação"])


# 📋 REGISTROS DIÁRIOS
with abas[0]:
    st.header("📋 Visualizar Registros Diários")
    st.divider()
    st.subheader("➕ Adicionar Novo Registro Diário")

    with st.form("form_registro_diario"):
        paciente = "Fernando Paiva"
        st.markdown(f"👤 Paciente: **{paciente}**")

        from datetime import datetime
        data = datetime.now().strftime("%d-%m-%Y %H:%M:%S")
        st.markdown(f"🕒 Data do Registro: **{data}**")

        temperatura_str = st.text_input("Temperatura (°C)", placeholder="Ex: 36,5")
        opcoes_sono = [f"{h}h {m}min" if m > 0 else f"{h}h" for h in range(3, 13) for m in [0, 30]]
        sono = st.selectbox("Horas de Sono", opcoes_sono)
        pressao = st.text_input("Pressão Arterial (ex: 120x80)")
        observacao = st.text_area("Observação comportamental e de saúde do paciente")
        observacao_geral = st.text_area("Observação de entrada e saída do cuidador")

        nomes_cuidadores = df_cuidadores["nome"].unique().tolist() if not df_cuidadores.empty else []
        cuidador = st.selectbox("Cuidador Responsável", nomes_cuidadores)

        # 🔍 Buscar medicamentos disponíveis
        df_medicamentos = supabase.table("medicamentos").select("id", "nome", "dosagem").execute().data
        opcoes_medicamentos = {
            f"{m['nome']} ({m['dosagem']})": m["id"] for m in df_medicamentos
        }
        medicamentos_selecionados = st.multiselect(
            "Medicamentos administrados hoje",
            options=list(opcoes_medicamentos.keys())
        )

        enviar = st.form_submit_button("Salvar Registro")

        if enviar:
            try:
                temperatura = float(temperatura_str.replace(",", "."))
            except ValueError:
                st.error("⚠️ Temperatura inválida. Use formato como 36,5")
                temperatura = None

            if temperatura and cuidador:
                novo_registro = {
                    "data": data,
                    "temperatura": temperatura,
                    "pressao": pressao,
                    "sono": sono,
                    "observacao": observacao,
                    "cuidador": cuidador,
                    "observacao_geral": observacao_geral
                }
                resultado = supabase.table("registros_diarios").insert(novo_registro).execute()
                registro_id = resultado.data[0]["id"]

                # 🔗 Atualizar medicamentos com o registro_id
                for label in medicamentos_selecionados:
                    medicamento_id = opcoes_medicamentos[label]
                    supabase.table("medicamentos").update({"registro_id": registro_id}).eq("id", medicamento_id).execute()

                st.success("✅ Registro diário salvo com sucesso e medicamentos vinculados!")

    # Exibição dos registros
    if not df_registros.empty:
        if status_filtrar and col_filtro:
            df_exibir = df_registros[df_registros[col_filtro] == valor_filtro]
        else:
            df_exibir = df_registros.copy()

        st.dataframe(df_exibir[colunas_selecionadas])
    else:
        st.warning("Nenhum registro disponível.")

# 🧑‍⚕️ CUIDADORES
with abas[1]:
    st.subheader("Cadastro de Cuidadores")

    with st.form(key="form_cuidadores"):
        nome = st.text_input("Nome do Cuidador")
        idade = st.number_input("Idade", min_value=18, max_value=100)
        telefone = st.text_input("Telefone")
        especialidade = st.selectbox("Especialidade", ["Geral", "Técnico em Enfermagem", "Enfermeiro", "Cuidador", "Outro"])
        disponibilidade = st.slider("Disponibilidade Semanal de Plantão (em Dias)", 0, 4)

        submit = st.form_submit_button("Salvar Cuidador")

        if submit and nome:
            novo = {
                "nome": nome,
                "idade": idade,
                "telefone": telefone,
                "especialidade": especialidade,
                "disponibilidade": disponibilidade
            }
            supabase.table("cuidadores").insert(novo).execute()
            st.success(f"Cuidador {nome} cadastrado com sucesso! 🎉")

    st.divider()
    st.subheader("Lista de Cuidadores Registrados")
    if not df_cuidadores.empty:
        st.dataframe(df_cuidadores)
    else:
        st.info("Nenhum cuidador cadastrado ainda.")

# 💊 MEDICAMENTOS
with abas[2]:
    st.subheader("Registro de Medicamentos")

    with st.form("form_medicamentos"):
        cuidador_nome = st.selectbox("Cuidador Responsável", df_cuidadores["nome"].tolist())
        nome_medicamento = st.text_input("Nome do Medicamento")
        dosagem = st.text_input("Dosagem")
        frequencia = st.selectbox("Frequência", ["1x ao dia", "2x ao dia", "3x ao dia", "A cada 8h", "Sob demanda"])
        horario = st.time_input("Horário de Administração", value=time(8, 0))
        observacoes = st.text_area("Observações Adicionais")

        salvar_med = st.form_submit_button("Salvar Medicamento")

        if salvar_med and nome_medicamento and cuidador_nome:
            # 🔗 Buscar o ID do cuidador
            cuidador_id = df_cuidadores[df_cuidadores["nome"] == cuidador_nome]["id"].values[0]

            # 💾 Inserir medicamento diretamente
            novo = {
                "nome": nome_medicamento,
                "dosagem": dosagem,
                "frequencia": frequencia,
                "horario": horario.strftime("%H:%M"),
                "cuidador_id": cuidador_id,
                "observacoes": observacoes
            }
            supabase.table("medicamentos").insert(novo).execute()
            st.success(f"Medicamento {nome_medicamento} registrado com sucesso! ✅")

    # 📊 Mostrar todos os medicamentos registrados
    st.markdown("### Medicamentos Registrados")
    dados_medicamentos = supabase.table("medicamentos").select("*").execute()
    
    df_medicamentos = pd.DataFrame(dados_medicamentos.data)

    # 🧹 Remover colunas indesejadas
    colunas_ocultas = ["id", "cuidador_id"]
    df_visivel = df_medicamentos.drop(columns=colunas_ocultas, errors="ignore")

    if not df_visivel.empty:
        st.dataframe(df_visivel)
    else:
        st.info("Nenhum medicamento registrado ainda.")
       

# 🍽️ ALIMENTAÇÃO
with abas[3]:
    st.subheader("Registro de Refeições")

    with st.form("form_alimentacao"):
        cuidador_nome = st.selectbox("Cuidador Responsável", df_cuidadores["nome"].tolist())
        refeicao = st.selectbox("Tipo de Refeição", ["Café da Manhã", "Almoço", "Lanche", "Jantar", "Ceia"])
        alimentos = st.text_area("Alimentos Oferecidos")
        quantidade = st.text_input("Quantidade Aproximada")
        aceitou = st.radio("Aceitação da refeição:", ["Sim", "Parcialmente", "Recusou"])
        horario = st.time_input("Horário da Refeição", value=time(12, 0))
        observacoes = st.text_area("Observações adicionais")

        salvar_refeicao = st.form_submit_button("Salvar Refeição")

        if salvar_refeicao and cuidador_nome:
            cuidador_id = df_cuidadores[df_cuidadores["nome"] == cuidador_nome]["id"].values[0]

            novo = {
                "refeicao": refeicao,
                "alimentos": alimentos,
                "quantidade": quantidade,
                "aceitou": aceitou,
                "horario": horario.strftime("%H:%M"),
                "responsavel": cuidador_nome,
                "cuidador_id": cuidador_id,
                "observacoes": observacoes
            }
            supabase.table("alimentacao").insert(novo).execute()
            st.success(f"Refeição registrada: {refeicao} às {horario.strftime('%H:%M')} 🕒")

    # 📊 Mostrar todas as refeições registradas
    st.divider()
    st.subheader("Refeições Registradas")
    dados_refeicoes = supabase.table("alimentacao").select("*").execute()
    df_refeicoes = pd.DataFrame(dados_refeicoes.data)

    # 🧹 Remover colunas indesejadas
    colunas_ocultas = ["id", "cuidador_id"]
    df_visivel = df_refeicoes.drop(columns=colunas_ocultas, errors="ignore")

    if not df_visivel.empty:
        st.dataframe(df_visivel)
    else:
        st.info("Nenhum registro de alimentação ainda.")

if st.button("Forçar token manual"):
    st.session_state["token_input"] = "SEU_ACCESS_TOKEN_AQUI"

