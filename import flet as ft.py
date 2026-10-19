import flet as ft
import json
import os
import shutil
import platform
from datetime import datetime
from fpdf import FPDF

# --- CONFIGURAÇÕES GLOBAIS E DIRETÓRIOS ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ASSETS_DIR = os.path.join(BASE_DIR, "assets")

if not os.path.exists(ASSETS_DIR):
    os.makedirs(ASSETS_DIR)

ARQUIVOS = {
    "os": os.path.join(BASE_DIR, "banco_dados_os.json"),
    "clientes": os.path.join(BASE_DIR, "banco_clientes.json"),
    "config": os.path.join(BASE_DIR, "config_empresa.json"),
    "agenda": os.path.join(BASE_DIR, "banco_agenda.json"), 
    "backup": os.path.join(BASE_DIR, "backup_sistema"),
}

CORES = {
    "bg": "#f4f6f9",
    "menu": "#e2e8f0", 
    "btn_primary": "#3498db",
    "btn_danger": "#e74c3c",
    "btn_success": "#27ae60",
    "text": "#2c3e50",
    "card": "#ffffff"
}

def inicializar_arquivos():
    if not os.path.exists(ARQUIVOS["backup"]): os.makedirs(ARQUIVOS["backup"])
    for arq in [ARQUIVOS["os"], ARQUIVOS["clientes"], ARQUIVOS["config"], ARQUIVOS["agenda"]]:
        if not os.path.exists(arq):
            with open(arq, 'w', encoding='utf-8') as f:
                json.dump({} if arq == ARQUIVOS["config"] else [], f)

def ler_json(arquivo):
    try:
        with open(arquivo, 'r', encoding='utf-8') as f: return json.load(f)
    except: return {} if arquivo == ARQUIVOS["config"] else []

def salvar_json(arquivo, dados):
    try: shutil.copy(arquivo, os.path.join(ARQUIVOS["backup"], os.path.basename(arquivo)))
    except: pass
    with open(arquivo, 'w', encoding='utf-8') as f:
        json.dump(dados, f, indent=4, ensure_ascii=False)

def gerar_id_os():
    dados = ler_json(ARQUIVOS["os"])
    if not dados: return "20260001"
    ultimo_id = str(dados[-1]["id"])
    if ultimo_id.startswith("2026") and len(ultimo_id) == 8:
        try: return f"2026{int(ultimo_id[4:]) + 1:04d}"
        except: pass
    return f"2026{len(dados) + 1:04d}"

def safe_float(valor):
    if not valor: return 0.0
    try: return float(str(valor).replace(",", ".").strip())
    except ValueError: return 0.0

# --- INTERFACE PRINCIPAL ---
def main(page: ft.Page):
    page.title = "OS Manager 2026"
    page.theme_mode = ft.ThemeMode.LIGHT
    page.bgcolor = CORES["bg"]
    page.padding = 0

    inicializar_arquivos()

    conteudo_principal = ft.Container(expand=True, padding=20)
    estado_app = {"os_em_edicao": None}
    imagens_os_atual = []

    # ==========================================
    # FILE PICKERS & UPLOADS
    # ==========================================
    c_logo_global = ft.TextField(label="Nome da Logo Selecionada", expand=True, read_only=True)

    def on_upload_geral(e: ft.FilePickerUploadEvent):
        page.update()

    def on_logo_selecionada(e: ft.FilePickerResultEvent):
        if e.files and len(e.files) > 0:
            f = e.files[0]
            c_logo_global.value = f.name
            upload_url = page.get_upload_url(f.name, 600)
            logo_picker.upload([ft.FilePickerUploadFile(f.name, upload_url=upload_url)])
            page.update()

    logo_picker = ft.FilePicker(on_result=on_logo_selecionada, on_upload=on_upload_geral)
    
    def atualizar_galeria():
        galeria_imagens.controls.clear()
        for img_nome in imagens_os_atual:
            def btn_remover(e, p=img_nome):
                if p in imagens_os_atual:
                    imagens_os_atual.remove(p)
                atualizar_galeria()
            galeria_imagens.controls.append(
                ft.Stack([
                    ft.Image(src=img_nome, width=150, height=150, fit=ft.ImageFit.COVER, border_radius=5),
                    ft.Container(
                        ft.IconButton(ft.icons.DELETE, icon_color="white", bgcolor="red", on_click=btn_remover),
                        alignment=ft.alignment.top_right, padding=5
                    )
                ], width=150, height=150)
            )
        page.update()

    def on_os_img_selecionada(e: ft.FilePickerResultEvent):
        if e.files:
            for f in e.files:
                upload_url = page.get_upload_url(f.name, 600)
                if f.name not in imagens_os_atual:
                    imagens_os_atual.append(f.name)
                os_img_picker.upload([ft.FilePickerUploadFile(f.name, upload_url=upload_url)])
            atualizar_galeria()

    os_img_picker = ft.FilePicker(on_result=on_os_img_selecionada, on_upload=on_upload_geral)
    page.overlay.extend([logo_picker, os_img_picker])

    # ==========================================
    # TELA 0: DASHBOARD E GERAÇÃO DE PDF
    # ==========================================
    def carregar_dashboard():
        estado_app["os_em_edicao"] = None
        conteudo_principal.content = ft.Column([
            ft.Text("Painel de Controle", size=28, weight="bold", color=CORES["text"]),
            campo_busca_dash,
            ft.Row([tabela_os], scroll=ft.ScrollMode.ALWAYS, expand=True)
        ], expand=True)
        atualizar_tabela_dashboard()
        page.update()

    def acao_gerar_pdf(id_os):
        dados = ler_json(ARQUIVOS["os"])
        config_emp = ler_json(ARQUIVOS["config"])
        os_selecionada = next((x for x in dados if str(x["id"]) == str(id_os)), None)
        
        if os_selecionada:
            def pt(texto): return str(texto).encode('latin-1', 'replace').decode('latin-1')

            pdf = FPDF()
            pdf.add_page()
            
            logo_path = config_emp.get("logo", "")
            tem_logo = False
            
            caminho_logo = os.path.join(ASSETS_DIR, logo_path) if logo_path else ""

            if caminho_logo and os.path.exists(caminho_logo):
                try:
                    pdf.image(caminho_logo, x=10, y=10, w=30)
                    tem_logo = True
                except: pass
            
            nome_empresa = config_emp.get("nome", "MINHA EMPRESA OFICINA")
            tel_empresa = config_emp.get("telefone", "(00) 0000-0000")
            cnpj_empresa = config_emp.get("cnpj", "00.000.000/0000-00")
            email_empresa = config_emp.get("email", "contato@empresa.com.br")
            site_empresa = config_emp.get("site", "www.empresa.com.br")
            
            if tem_logo:
                pdf.set_xy(45, 10)
                pdf.set_font("Arial", 'B', 16)
                pdf.cell(0, 7, txt=pt(nome_empresa), ln=True, align='L')
                pdf.set_x(45)
                pdf.set_font("Arial", '', 9)
                pdf.cell(0, 5, txt=pt(f"CNPJ: {cnpj_empresa} | Tel: {tel_empresa}"), ln=True, align='L')
                pdf.set_x(45)
                pdf.cell(0, 5, txt=pt(f"Email: {email_empresa} | Site: {site_empresa}"), ln=True, align='L')
                pdf.ln(12)
            else:
                pdf.set_font("Arial", 'B', 18)
                pdf.cell(0, 8, txt=pt(nome_empresa), ln=True, align='C')
                pdf.set_font("Arial", '', 9)
                pdf.cell(0, 5, txt=pt(f"CNPJ: {cnpj_empresa} | Tel: {tel_empresa}"), ln=True, align='C')
                pdf.cell(0, 5, txt=pt(f"Email: {email_empresa} | Site: {site_empresa}"), ln=True, align='C')
                pdf.ln(10)
            
            pdf.set_font("Arial", 'B', 14)
            pdf.cell(0, 10, txt=f"ORDEM DE SERVICO #{os_selecionada['id']}", ln=True, align='C', border='B')
            pdf.ln(2)
            
            pdf.set_font("Arial", 'B', 9)
            pdf.cell(10, 5, txt="Data:")
            pdf.set_font("Arial", '', 9)
            pdf.cell(25, 5, txt=pt(os_selecionada.get('data', '')))
            
            pdf.set_font("Arial", 'B', 9)
            pdf.cell(12, 5, txt="Status:")
            pdf.set_font("Arial", '', 9)
            pdf.cell(35, 5, txt=pt(os_selecionada.get('status', '')))
            
            tec_nome = os_selecionada.get('Técnico Resp.', '')
            pdf.set_font("Arial", 'B', 9)
            pdf.cell(22, 5, txt="Tecnico Resp.:")
            pdf.set_font("Arial", '', 9)
            pdf.cell(86, 5, txt=pt(tec_nome), ln=True)
            pdf.ln(3)
            
            pdf.set_font("Arial", 'B', 11)
            pdf.set_fill_color(240, 240, 240)
            pdf.cell(0, 8, txt=" DADOS DO CLIENTE", border=1, ln=True, fill=True)
            
            resp_local = os_selecionada.get('Responsável no Local', '')
            pdf.set_font("Arial", 'B', 10)
            pdf.cell(28, 6, txt="Cliente/Razao:", border='L')
            pdf.set_font("Arial", '', 10)
            pdf.cell(67, 6, txt=pt(os_selecionada.get('Cliente', '')), border='')
            pdf.set_font("Arial", 'B', 10)
            pdf.cell(25, 6, txt="Resp (Local):", border='')
            pdf.set_font("Arial", '', 10)
            pdf.cell(70, 6, txt=pt(resp_local), border='R', ln=True)
            
            pdf.set_font("Arial", 'B', 10)
            pdf.cell(22, 6, txt="CPF/CNPJ:", border='L')
            pdf.set_font("Arial", '', 10)
            pdf.cell(41, 6, txt=pt(os_selecionada.get('CPF/CNPJ', '')), border='')
            pdf.set_font("Arial", 'B', 10)
            pdf.cell(18, 6, txt="Telefone:", border='')
            pdf.set_font("Arial", '', 10)
            pdf.cell(42, 6, txt=pt(os_selecionada.get('Telefone', '')), border='')
            pdf.set_font("Arial", 'B', 10)
            pdf.cell(13, 6, txt="Email:", border='')
            pdf.set_font("Arial", '', 10)
            pdf.cell(54, 6, txt=pt(os_selecionada.get('Email', '')), border='R', ln=True)
            
            pdf.set_font("Arial", 'B', 10)
            pdf.cell(18, 6, txt="Endereco:", border='L')
            pdf.set_font("Arial", '', 10)
            end_str = pt(f"{os_selecionada.get('Endereço', '')}, {os_selecionada.get('Número', '')}")
            pdf.cell(92, 6, txt=end_str, border='')
            pdf.set_font("Arial", 'B', 10)
            pdf.cell(28, 6, txt="Complemento:", border='')
            pdf.set_font("Arial", '', 10)
            pdf.cell(52, 6, txt=pt(os_selecionada.get('Complemento', '')), border='R', ln=True)
            
            pdf.set_font("Arial", 'B', 10)
            pdf.cell(14, 6, txt="Bairro:", border='LB')
            pdf.set_font("Arial", '', 10)
            pdf.cell(56, 6, txt=pt(os_selecionada.get('Bairro', '')), border='B')
            pdf.set_font("Arial", 'B', 10)
            pdf.cell(16, 6, txt="Cidade:", border='B')
            pdf.set_font("Arial", '', 10)
            pdf.cell(60, 6, txt=pt(os_selecionada.get('Cidade', '')), border='B')
            pdf.set_font("Arial", 'B', 10)
            pdf.cell(10, 6, txt="CEP:", border='B')
            pdf.set_font("Arial", '', 10)
            pdf.cell(34, 6, txt=pt(os_selecionada.get('CEP', '')), border='RB', ln=True)
            pdf.ln(4)
            
            pdf.set_font("Arial", 'B', 11)
            pdf.cell(0, 8, txt=" EQUIPAMENTO", border=1, ln=True, fill=True)
            
            pdf.set_font("Arial", 'B', 10)
            pdf.cell(18, 6, txt="Aparelho:", border='L')
            pdf.set_font("Arial", '', 10)
            pdf.cell(47, 6, txt=pt(os_selecionada.get('Aparelho', '')), border='')
            pdf.set_font("Arial", 'B', 10)
            pdf.cell(14, 6, txt="Marca:", border='')
            pdf.set_font("Arial", '', 10)
            pdf.cell(46, 6, txt=pt(os_selecionada.get('Marca', '')), border='')
            pdf.set_font("Arial", 'B', 10)
            pdf.cell(16, 6, txt="Modelo:", border='')
            pdf.set_font("Arial", '', 10)
            pdf.cell(49, 6, txt=pt(os_selecionada.get('Modelo', '')), border='R', ln=True)
            
            serie_val = os_selecionada.get('Número de Série', '')
            pdf.set_font("Arial", 'B', 10)
            pdf.cell(20, 6, txt="Serie/IMEI:", border='L')
            pdf.set_font("Arial", '', 10)
            pdf.cell(75, 6, txt=pt(serie_val), border='')
            pdf.set_font("Arial", 'B', 10)
            pdf.cell(15, 6, txt="Senha:", border='')
            pdf.set_font("Arial", '', 10)
            pdf.cell(80, 6, txt=pt(os_selecionada.get('Senha de Acesso', '')), border='R', ln=True)
            
            pdf.set_font("Arial", 'B', 10)
            pdf.cell(0, 6, txt=" Estado Fisico/Avarias:", border='LR', ln=True)
            pdf.set_font("Arial", '', 10)
            avarias = os_selecionada.get('Estado Físico / Avarias', '')
            pdf.multi_cell(0, 5, txt=pt(f" {avarias}" if avarias else " "), border='LR')
            
            pdf.set_font("Arial", 'B', 10)
            pdf.cell(0, 6, txt=" Defeito Relatado:", border='LR', ln=True)
            pdf.set_font("Arial", '', 10)
            defeito = os_selecionada.get('Defeito Relatado', '')
            pdf.multi_cell(0, 5, txt=pt(f" {defeito}" if defeito else " "), border='LRB')
            pdf.ln(4)
            
            pdf.set_font("Arial", 'B', 11)
            pdf.cell(0, 8, txt=" SERVICOS E PECAS", border=1, ln=True, fill=True)
            pdf.set_font("Arial", 'B', 10)
            pdf.cell(140, 6, txt="Descricao", border=1)
            pdf.cell(50, 6, txt="Valor (R$)", border=1, ln=True, align='R')
            
            pdf.set_font("Arial", '', 10)
            for item in os_selecionada.get("itens", []):
                pdf.cell(140, 6, txt=pt(item.get('desc', '')), border=1)
                pdf.cell(50, 6, txt=f"{safe_float(item.get('valor', 0)):.2f}", border=1, ln=True, align='R')
            pdf.ln(4)
            
            pdf.set_font("Arial", 'B', 12)
            pdf.cell(140, 8, txt="TOTAL GERAL:", border=0, align='R')
            pdf.cell(50, 8, txt=f"R$ {safe_float(os_selecionada.get('total_geral', 0)):.2f}", border=1, ln=True, align='R')
            pdf.ln(4)

            laudo_texto = str(os_selecionada.get('Laudo', '')).strip()
            if laudo_texto:
                pdf.set_font("Arial", 'B', 11)
                pdf.cell(0, 8, txt=" LAUDO TECNICO / DIAGNOSTICO", border=1, ln=True, fill=True)
                pdf.set_font("Arial", '', 10)
                pdf.multi_cell(0, 6, txt=pt(laudo_texto), border=1)
                pdf.ln(4)

            obs_texto = str(os_selecionada.get('Observações / Garantia', '')).strip()
            if obs_texto:
                pdf.set_font("Arial", 'B', 11)
                pdf.cell(0, 8, txt=" OBSERVACOES / GARANTIA", border=1, ln=True, fill=True)
                pdf.set_font("Arial", '', 10)
                pdf.multi_cell(0, 6, txt=pt(obs_texto), border=1)
                pdf.ln(4)

            imagens_salvas = os_selecionada.get("imagens", [])
            if imagens_salvas:
                pdf.add_page()
                pdf.set_font("Arial", 'B', 12)
                pdf.cell(0, 10, txt="ANEXOS FOTOGRAFICOS", ln=True, align='C', border='B')
                pdf.ln(5)
                
                x_pos = 10
                y_pos = pdf.get_y()
                
                for img_nome in imagens_salvas:
                    caminho_real = os.path.join(ASSETS_DIR, img_nome)
                    if not os.path.exists(caminho_real) and os.path.exists(img_nome):
                        caminho_real = img_nome
                        
                    if os.path.exists(caminho_real):
                        if y_pos > 220:
                            pdf.add_page()
                            x_pos = 10
                            y_pos = pdf.get_y()
                        try:
                            pdf.image(caminho_real, x=x_pos, y=y_pos, w=85)
                            x_pos += 95
                            if x_pos > 110:
                                x_pos = 10
                                y_pos += 90
                        except Exception as erro_img:
                            print(f"Aviso: Imagem ignorada no PDF ({caminho_real}). Erro: {erro_img}")

            # ==========================================
            # NOVO SISTEMA ANTI-BLOQUEIO DE PDF
            # ==========================================
            nome_pdf_final = f"OS_{id_os}.pdf"
            caminho_arquivo_pdf = os.path.join(ASSETS_DIR, nome_pdf_final)
            
            try:
                pdf.output(caminho_arquivo_pdf)
            except Exception as e:
                page.snack_bar = ft.SnackBar(ft.Text(f"⚠️ Erro ao gerar PDF: {e}", color="white"), bgcolor=CORES["btn_danger"])
                page.snack_bar.open = True; page.update(); return
            
            try:
                if platform.system() == 'Windows':
                    os.startfile(caminho_arquivo_pdf)
                elif platform.system() == 'Darwin':
                    os.system(f"open '{caminho_arquivo_pdf}'")
            except: pass

            def fechar_dialogo_pdf(e):
                dialogo_pdf.open = False
                page.update()

            dialogo_pdf = ft.AlertDialog(
                title=ft.Text("✅ PDF Gerado!"),
                content=ft.Container(
                    content=ft.Text(f"O documento da OS #{id_os} foi criado.\nClique no botão abaixo para visualizar."),
                    padding=10
                ),
                actions=[
                    ft.ElevatedButton(
                        "📄 ABRIR PDF", 
                        url=f"/{nome_pdf_final}",  
                        bgcolor=CORES["btn_primary"], 
                        color="white"
                    ),
                    ft.TextButton("Fechar", on_click=fechar_dialogo_pdf)
                ],
                actions_alignment=ft.MainAxisAlignment.END,
            )
            
            page.overlay.append(dialogo_pdf)
            dialogo_pdf.open = True
            page.update()

    def acao_editar_os(e):
        os_dict = e.control.data
        estado_app["os_em_edicao"] = os_dict
        menu_lateral.selected_index = 1
        menu_lateral.update()
        carregar_nova_os(os_dict)

    def atualizar_tabela_dashboard(e=None):
        dados = ler_json(ARQUIVOS["os"])
        dados.reverse()
        termo = campo_busca_dash.value.lower() if campo_busca_dash.value else ""
        
        linhas = []
        for item in dados:
            c_nome = item.get("Cliente", item.get("cliente", ""))
            if termo in str(item.get("id")).lower() or termo in c_nome.lower():
                linhas.append(
                    ft.DataRow(cells=[
                        ft.DataCell(ft.Text(str(item.get("id")))),
                        ft.DataCell(ft.Text(item.get("data", ""))),
                        ft.DataCell(ft.Text(c_nome)),
                        ft.DataCell(ft.Text(item.get("status", "Orçamento"))),
                        ft.DataCell(ft.Text(f"R$ {safe_float(item.get('total_geral', 0)):.2f}")),
                        ft.DataCell(ft.Row([
                            ft.IconButton(icon=ft.icons.EDIT, icon_color="blue", tooltip="Editar", data=item, on_click=acao_editar_os),
                            ft.IconButton(icon=ft.icons.PICTURE_AS_PDF, icon_color="red", tooltip="Gerar PDF", on_click=lambda e, id_os=item['id']: acao_gerar_pdf(id_os))
                        ]))
                    ])
                )
        tabela_os.rows = linhas
        page.update()

    campo_busca_dash = ft.TextField(label="🔍 Buscar OS ou Cliente", on_change=atualizar_tabela_dashboard)
    tabela_os = ft.DataTable(
        columns=[
            ft.DataColumn(ft.Text("ID")), ft.DataColumn(ft.Text("Data")),
            ft.DataColumn(ft.Text("Cliente")), ft.DataColumn(ft.Text("Status")),
            ft.DataColumn(ft.Text("Total")), ft.DataColumn(ft.Text("Ações")),
        ], rows=[]
    )

    # ==========================================
    # TELA 1: NOVA / EDITAR OS
    # ==========================================
    itens_servico = []
    lista_servicos_ui = ft.Column()
    galeria_imagens = ft.Row(wrap=True, spacing=15, run_spacing=15)

    def carregar_nova_os(os_dados=None):
        itens_servico.clear()
        lista_servicos_ui.controls.clear()
        imagens_os_atual.clear()
        
        titulo_tela = "EDITAR ORDEM DE SERVIÇO" if os_dados else "NOVA ORDEM DE SERVIÇO"

        txt_cpf = ft.TextField(label="CPF/CNPJ", width=200)
        txt_cliente = ft.TextField(label="Cliente (Razão Social/Nome)", expand=True)
        txt_resp = ft.TextField(label="Responsável no Local", width=250)
        txt_tel = ft.TextField(label="Telefone", width=200)
        txt_email = ft.TextField(label="Email", expand=True)
        txt_cep = ft.TextField(label="CEP", width=150)
        txt_cidade = ft.TextField(label="Cidade", width=250)
        txt_end = ft.TextField(label="Endereço", expand=True)
        txt_num = ft.TextField(label="Número", width=100)
        txt_comp = ft.TextField(label="Complemento", width=150)
        txt_bairro = ft.TextField(label="Bairro", width=200)

        txt_aparelho = ft.TextField(label="Aparelho", width=250)
        txt_marca = ft.TextField(label="Marca", width=200)
        txt_modelo = ft.TextField(label="Modelo", expand=True)
        txt_serie = ft.TextField(label="Número de Série", expand=True)
        txt_senha = ft.TextField(label="Senha de Acesso", width=200)
        txt_estado = ft.TextField(label="Estado Físico / Avarias", multiline=True, expand=True)
        txt_defeito = ft.TextField(label="Defeito Relatado", multiline=True, expand=True)

        txt_tec = ft.TextField(label="Técnico Resp.", width=300)
        txt_taxa = ft.TextField(label="Taxa Visita (R$)", width=150, value="0")
        txt_gasto = ft.TextField(label="Gasto Extra (R$)", width=150, value="0")
        
        txt_laudo = ft.TextField(label="Laudo Técnico / Diagnóstico", multiline=True, min_lines=3, expand=True)
        txt_obs = ft.TextField(label="Observações / Garantia", multiline=True, expand=True)

        dropdown_status = ft.Dropdown(label="Status da OS", value="Orçamento", width=200, options=[
            ft.dropdown.Option("Orçamento"), ft.dropdown.Option("Aprovado"), 
            ft.dropdown.Option("Executado"), ft.dropdown.Option("Cancelado")
        ])

        def adicionar_item_linha(desc="", valor="0", custo="0"):
            txt_desc = ft.TextField(label="Descrição do Serviço/Peça", expand=True, value=desc)
            txt_val = ft.TextField(label="Valor (R$)", width=120, value=str(valor))
            txt_cus = ft.TextField(label="Custo (R$)", width=120, value=str(custo))
            
            def remover_linha(e):
                lista_servicos_ui.controls.remove(linha)
                itens_servico.remove({"desc": txt_desc, "valor": txt_val, "custo": txt_cus})
                page.update()

            linha = ft.Row([txt_desc, txt_val, txt_cus, ft.IconButton(icon=ft.icons.DELETE, icon_color="red", on_click=remover_linha)], wrap=True, spacing=15, run_spacing=15)
            itens_servico.append({"desc": txt_desc, "valor": txt_val, "custo": txt_cus})
            lista_servicos_ui.controls.append(linha)
            if page.route: page.update()

        if os_dados:
            txt_cpf.value = str(os_dados.get("CPF/CNPJ", ""))
            txt_cliente.value = str(os_dados.get("Cliente", ""))
            txt_resp.value = str(os_dados.get("Responsável no Local", ""))
            txt_tel.value = str(os_dados.get("Telefone", ""))
            txt_email.value = str(os_dados.get("Email", ""))
            txt_cep.value = str(os_dados.get("CEP", ""))
            txt_cidade.value = str(os_dados.get("Cidade", ""))
            txt_end.value = str(os_dados.get("Endereço", ""))
            txt_num.value = str(os_dados.get("Número", ""))
            txt_comp.value = str(os_dados.get("Complemento", ""))
            txt_bairro.value = str(os_dados.get("Bairro", ""))
            
            txt_aparelho.value = str(os_dados.get("Aparelho", ""))
            txt_marca.value = str(os_dados.get("Marca", ""))
            txt_modelo.value = str(os_dados.get("Modelo", ""))
            txt_serie.value = str(os_dados.get("Número de Série", ""))
            txt_senha.value = str(os_dados.get("Senha de Acesso", ""))
            txt_estado.value = str(os_dados.get("Estado Físico / Avarias", ""))
            txt_defeito.value = str(os_dados.get("Defeito Relatado", ""))
            
            txt_tec.value = str(os_dados.get("Técnico Resp.", ""))
            txt_taxa.value = str(os_dados.get("Taxa Visita (R$)", "0"))
            txt_gasto.value = str(os_dados.get("Gasto Extra (R$)", "0"))
            
            txt_laudo.value = str(os_dados.get("Laudo", ""))
            txt_obs.value = str(os_dados.get("Observações / Garantia", ""))
            dropdown_status.value = str(os_dados.get("status", "Orçamento"))
            
            imagens_os_atual.extend(os_dados.get("imagens", []))

            for item in os_dados.get("itens", []):
                adicionar_item_linha(desc=item.get("desc", ""), valor=item.get("valor", 0), custo=item.get("custo", 0))
        
        atualizar_galeria() 

        def salvar_os(e):
            if not txt_cliente.value.strip():
                page.snack_bar = ft.SnackBar(ft.Text("⚠️ Cliente é obrigatório!", color="white"), bgcolor="red")
                page.snack_bar.open = True; page.update()
                return

            tot_geral = sum(safe_float(i["valor"].value) for i in itens_servico) + safe_float(txt_taxa.value)
            tot_custo = sum(safe_float(i["custo"].value) for i in itens_servico) + safe_float(txt_gasto.value)

            dados_para_salvar = {
                "id": estado_app["os_em_edicao"]["id"] if estado_app["os_em_edicao"] else gerar_id_os(),
                "data": estado_app["os_em_edicao"]["data"] if estado_app["os_em_edicao"] else datetime.now().strftime("%d/%m/%Y"),
                "status": dropdown_status.value, 
                "total_geral": tot_geral, 
                "total_custo": tot_custo,
                "CPF/CNPJ": txt_cpf.value, "Cliente": txt_cliente.value, "Responsável no Local": txt_resp.value,
                "Telefone": txt_tel.value, "Email": txt_email.value, "CEP": txt_cep.value, "Cidade": txt_cidade.value,
                "Endereço": txt_end.value, "Número": txt_num.value, "Complemento": txt_comp.value, "Bairro": txt_bairro.value,
                "Aparelho": txt_aparelho.value, "Marca": txt_marca.value, "Modelo": txt_modelo.value, "Número de Série": txt_serie.value,
                "Senha de Acesso": txt_senha.value, "Estado Físico / Avarias": txt_estado.value, "Defeito Relatado": txt_defeito.value,
                "Técnico Resp.": txt_tec.value, "Taxa Visita (R$)": txt_taxa.value, "Gasto Extra (R$)": txt_gasto.value,
                "Laudo": txt_laudo.value, "Observações / Garantia": txt_obs.value,
                "imagens": list(imagens_os_atual),
                "itens": [{"desc": i["desc"].value, "valor": safe_float(i["valor"].value), "custo": safe_float(i["custo"].value)} for i in itens_servico]
            }

            bd = ler_json(ARQUIVOS["os"])
            if estado_app["os_em_edicao"]:
                for i, obj in enumerate(bd):
                    if obj["id"] == dados_para_salvar["id"]: bd[i] = dados_para_salvar; break
            else: bd.append(dados_para_salvar)
            salvar_json(ARQUIVOS["os"], bd)
            
            bd_clientes = ler_json(ARQUIVOS["clientes"])
            if txt_cpf.value and not any(c.get("CPF/CNPJ") == txt_cpf.value for c in bd_clientes):
                bd_clientes.append({"Nome": txt_cliente.value, "CPF/CNPJ": txt_cpf.value, "Telefone": txt_tel.value})
                salvar_json(ARQUIVOS["clientes"], bd_clientes)

            page.snack_bar = ft.SnackBar(ft.Text(f"✅ OS Salva com Sucesso!", color="white"), bgcolor=CORES["btn_success"])
            page.snack_bar.open = True
            
            estado_app["os_em_edicao"] = None
            menu_lateral.selected_index = 0
            carregar_dashboard()

        # ADICIONADO SPACING E RUN_SPACING EM TODOS OS ROWS PARA EVITAR TEXTOS SOBREPOSTOS
        sec_cliente = ft.Card(content=ft.Container(padding=15, content=ft.Column([
            ft.Text("1. Cliente e Contatos", weight="bold", size=18, color=CORES["btn_primary"]),
            ft.Row([txt_cpf, txt_cliente, txt_resp], wrap=True, spacing=15, run_spacing=15), 
            ft.Row([txt_tel, txt_email, txt_cep, txt_cidade], wrap=True, spacing=15, run_spacing=15), 
            ft.Row([txt_end, txt_num, txt_comp, txt_bairro], wrap=True, spacing=15, run_spacing=15)
        ])))

        sec_equip = ft.Card(content=ft.Container(padding=15, content=ft.Column([
            ft.Text("2. Aparelho e Informações Técnicas", weight="bold", size=18, color=CORES["btn_primary"]),
            ft.Row([txt_aparelho, txt_marca, txt_modelo], wrap=True, spacing=15, run_spacing=15), 
            ft.Row([txt_serie, txt_senha], wrap=True, spacing=15, run_spacing=15), 
            ft.Row([txt_estado], wrap=True, spacing=15, run_spacing=15),
            ft.Row([txt_defeito], wrap=True, spacing=15, run_spacing=15)
        ])))

        sec_fin = ft.Card(content=ft.Container(padding=15, content=ft.Column([
            ft.Text("3. Serviços e Financeiro", weight="bold", size=18, color=CORES["btn_primary"]),
            ft.Row([txt_tec, txt_taxa, txt_gasto, dropdown_status], wrap=True, spacing=15, run_spacing=15), ft.Divider(),
            ft.Text("Itens da OS:", weight="bold"), lista_servicos_ui,
            ft.ElevatedButton("+ Adicionar Serviço/Peça", bgcolor=CORES["btn_success"], color="white", on_click=lambda e: adicionar_item_linha()),
            ft.Row([txt_obs], wrap=True, spacing=15, run_spacing=15)
        ])))

        sec_laudo = ft.Card(content=ft.Container(padding=15, content=ft.Column([
            ft.Text("4. Laudo Técnico e Imagens", weight="bold", size=18, color=CORES["btn_primary"]),
            ft.Row([txt_laudo], wrap=True, spacing=15, run_spacing=15),
            ft.ElevatedButton("📷 Adicionar Imagens do Equipamento", on_click=lambda _: os_img_picker.pick_files(allow_multiple=True, allowed_extensions=["png", "jpg", "jpeg"])),
            galeria_imagens
        ])))

        conteudo_principal.content = ft.Column([
            ft.Text(titulo_tela, size=28, weight="bold", color=CORES["text"]), 
            sec_cliente, sec_equip, sec_fin, sec_laudo,
            ft.ElevatedButton("💾 SALVAR ORDEM DE SERVIÇO", bgcolor=CORES["btn_primary"], color="white", height=50, on_click=salvar_os)
        ], scroll=ft.ScrollMode.ALWAYS, expand=True)
        page.update()

    # ==========================================
    # TELAS SECUNDÁRIAS MANTIDAS
    # ==========================================
    def carregar_agenda():
        txt_data = ft.TextField(label="Data", width=150)
        txt_desc = ft.TextField(label="Descrição / Cliente", expand=True)
        def salvar_agenda(e):
            if txt_data.value and txt_desc.value:
                bd = ler_json(ARQUIVOS["agenda"])
                bd.append({"data": txt_data.value, "desc": txt_desc.value})
                salvar_json(ARQUIVOS["agenda"], bd)
                carregar_agenda()
        
        linhas = [ft.ListTile(leading=ft.Icon(ft.icons.EVENT), title=ft.Text(i.get("data")), subtitle=ft.Text(i.get("desc"))) for i in ler_json(ARQUIVOS["agenda"])]
        conteudo_principal.content = ft.Column([
            ft.Text("Agenda de Visitas", size=28, weight="bold", color=CORES["text"]),
            ft.Card(content=ft.Container(padding=15, content=ft.Row([txt_data, txt_desc, ft.ElevatedButton("Adicionar", on_click=salvar_agenda)], wrap=True, spacing=15, run_spacing=15))),
            ft.Column(linhas, scroll=ft.ScrollMode.ALWAYS, expand=True)
        ], expand=True)
        page.update()

    def carregar_clientes():
        linhas = [ft.DataRow(cells=[ft.DataCell(ft.Text(c.get("Nome",""))), ft.DataCell(ft.Text(c.get("CPF/CNPJ",""))), ft.DataCell(ft.Text(c.get("Telefone","")))]) for c in ler_json(ARQUIVOS["clientes"])]
        tabela = ft.DataTable(columns=[ft.DataColumn(ft.Text("Nome")), ft.DataColumn(ft.Text("CPF/CNPJ")), ft.DataColumn(ft.Text("Telefone"))], rows=linhas)
        conteudo_principal.content = ft.Column([
            ft.Text("Base de Clientes", size=28, weight="bold", color=CORES["text"]), 
            ft.Row([tabela], scroll=ft.ScrollMode.ALWAYS, expand=True)
        ], expand=True)
        page.update()

    def carregar_relatorios():
        dados = ler_json(ARQUIVOS["os"])
        faturamento = sum(safe_float(d.get("total_geral", 0)) for d in dados if d.get("status") in ["Aprovado", "Executado"])
        custos = sum(safe_float(d.get("total_custo", 0)) for d in dados if d.get("status") in ["Aprovado", "Executado"])
        
        def kpi(t, v, c): return ft.Card(color=CORES["card"], content=ft.Container(padding=20, width=200, content=ft.Column([ft.Text(t, size=14, color="grey"), ft.Text(v, size=24, weight="bold", color=c)])))
        conteudo_principal.content = ft.Column([
            ft.Text("Relatórios e Faturamento", size=28, weight="bold", color=CORES["text"]),
            ft.Row([kpi("Faturamento", f"R$ {faturamento:.2f}", CORES["btn_primary"]), kpi("Custos", f"R$ {custos:.2f}", CORES["btn_danger"]), kpi("Lucro", f"R$ {(faturamento-custos):.2f}", CORES["btn_success"])], wrap=True, spacing=15, run_spacing=15)
        ], expand=True)
        page.update()

    def carregar_configuracoes():
        config_atual = ler_json(ARQUIVOS["config"])
        c_nome = ft.TextField(label="Nome da Empresa", value=config_atual.get("nome", ""), expand=True)
        c_cnpj = ft.TextField(label="CNPJ", value=config_atual.get("cnpj", ""), width=250)
        c_tel = ft.TextField(label="Telefone Comercial", value=config_atual.get("telefone", ""), width=250)
        c_email = ft.TextField(label="Email da Empresa", value=config_atual.get("email", ""), expand=True)
        c_site = ft.TextField(label="Site da Empresa", value=config_atual.get("site", ""), expand=True)
        
        c_logo_global.value = config_atual.get("logo", "")
        btn_procurar_logo = ft.IconButton(
            icon=ft.icons.IMAGE_SEARCH, 
            tooltip="Procurar Imagem", 
            icon_color=CORES["btn_primary"],
            on_click=lambda _: logo_picker.pick_files(allowed_extensions=["png", "jpg", "jpeg"])
        )

        def salvar_config(e):
            salvar_json(ARQUIVOS["config"], {
                "nome": c_nome.value, 
                "cnpj": c_cnpj.value, 
                "telefone": c_tel.value,
                "email": c_email.value,
                "site": c_site.value,
                "logo": c_logo_global.value
            })
            page.snack_bar = ft.SnackBar(ft.Text("Configurações Salvas!", color="white"), bgcolor=CORES["btn_success"])
            page.snack_bar.open = True; page.update()

        conteudo_principal.content = ft.Column([
            ft.Text("Configurações", size=28, weight="bold", color=CORES["text"]),
            ft.Card(content=ft.Container(padding=20, content=ft.Column([
                ft.Row([c_nome, c_cnpj], wrap=True, spacing=15, run_spacing=15),
                ft.Row([c_email, c_tel], wrap=True, spacing=15, run_spacing=15),
                ft.Row([c_site], wrap=True, spacing=15, run_spacing=15),
                ft.Row([c_logo_global, btn_procurar_logo], wrap=True, spacing=15, run_spacing=15),
                ft.ElevatedButton("Salvar Configurações", on_click=salvar_config, bgcolor=CORES["btn_primary"], color="white")
            ])))
        ], expand=True)
        page.update()

    # ==========================================
    # MENU LATERAL RESTAURADO
    # ==========================================
    def nav_change(e):
        idx = e.control.selected_index
        if idx == 1:
            estado_app["os_em_edicao"] = None

        telas = [carregar_dashboard, carregar_nova_os, carregar_agenda, carregar_clientes, carregar_relatorios, carregar_configuracoes]
        telas[idx]()

    menu_lateral = ft.NavigationRail(
        selected_index=0, 
        label_type=ft.NavigationRailLabelType.ALL, 
        min_width=100, 
        min_extended_width=200, 
        bgcolor=CORES["menu"],            
        indicator_color=ft.colors.WHITE,  
        group_alignment=-0.9,
        destinations=[
            ft.NavigationRailDestination(icon=ft.icons.DASHBOARD, label="Painel"),
            ft.NavigationRailDestination(icon=ft.icons.ADD_CIRCLE, label="Nova OS"),
            ft.NavigationRailDestination(icon=ft.icons.CALENDAR_MONTH, label="Agenda"),
            ft.NavigationRailDestination(icon=ft.icons.PEOPLE, label="Clientes"),
            ft.NavigationRailDestination(icon=ft.icons.ATTACH_MONEY, label="Relatórios"),
            ft.NavigationRailDestination(icon=ft.icons.SETTINGS, label="Configurações")
        ],
        on_change=nav_change, 
        expand=False
    )

    page.add(ft.Row([menu_lateral, ft.VerticalDivider(width=1), conteudo_principal], expand=True))
    carregar_dashboard()

ft.app(target=main, assets_dir="assets")