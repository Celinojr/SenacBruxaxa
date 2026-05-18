from flask import Flask, render_template, request, redirect, session, send_file
import sqlite3
import os
from datetime import datetime

# PDF
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib import colors

app = Flask(__name__)

app.secret_key = "123456"

# ----------------------------
# USUARIOS
# ----------------------------

usuarios = {

    "admin": {
        "senha": "123",
        "tipo": "admin"
    },

    "recepcao": {
        "senha": "123",
        "tipo": "funcionario"
    }

}

# ----------------------------
# CONECTAR BANCO (CORRIGIDO)
# ----------------------------

def conectar():

    caminho = os.path.join(
        os.path.dirname(__file__),
        "hotel.db"
    )

    print("Banco:", caminho)

    conn = sqlite3.connect(caminho)

    return conn

# ----------------------------
# CRIAR TABELAS
# ----------------------------

def criar_tabelas():

    conn = conectar()

    cursor = conn.cursor()

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS hospedes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nome TEXT,
        cpf TEXT,
        telefone TEXT,
        quarto TEXT,
        entrada TEXT,
        saida TEXT,
        diaria REAL,
        total REAL
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS reservas (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nome TEXT,
        quarto TEXT,
        entrada TEXT,
        saida TEXT
    )
    """)

    conn.commit()
    conn.close()

criar_tabelas()

# ----------------------------
# INICIO
# ----------------------------

@app.route("/")
def inicio():

    return redirect("/login")

# ----------------------------
# LOGIN
# ----------------------------

@app.route("/login")
def login():

    return render_template("login.html")

# ----------------------------
# AUTENTICAR
# ----------------------------

@app.route("/autenticar", methods=["POST"])
def autenticar():

    usuario = request.form.get("usuario")
    senha = request.form.get("senha")

    if usuario in usuarios:

        if usuarios[usuario]["senha"] == senha:

            session["logado"] = True
            session["usuario"] = usuario
            session["tipo"] = usuarios[usuario]["tipo"]

            return redirect("/menu")

    return "Usuário ou senha inválidos"

# ----------------------------
# MENU
# ----------------------------

@app.route("/menu")
def menu():

    if "logado" not in session:
        return redirect("/login")

    return render_template("index.html")

# ----------------------------
# CADASTRO
# ----------------------------

@app.route("/cadastro")
def cadastro():

    if "logado" not in session:
        return redirect("/login")

    return render_template("cadastro.html")

# ----------------------------
# SALVAR HOSPEDE
# ----------------------------

@app.route("/salvar", methods=["POST"])
def salvar():

    if "logado" not in session:
        return redirect("/login")

    nome = request.form.get("nome")
    cpf = request.form.get("cpf")
    telefone = request.form.get("telefone")
    quarto = request.form.get("quarto")
    entrada = request.form.get("entrada")
    saida = request.form.get("saida")
    diaria = float(request.form.get("diaria"))

    data_entrada = datetime.strptime(
        entrada,
        "%Y-%m-%d"
    )

    data_saida = datetime.strptime(
        saida,
        "%Y-%m-%d"
    )

    dias = (data_saida - data_entrada).days

    total = dias * diaria

    conn = conectar()
    cursor = conn.cursor()

    cursor.execute("""
    INSERT INTO hospedes
    (nome, cpf, telefone, quarto,
     entrada, saida, diaria, total)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """,
    (
        nome,
        cpf,
        telefone,
        quarto,
        entrada,
        saida,
        diaria,
        total
    ))

    conn.commit()
    conn.close()

    return redirect("/lista")

# ----------------------------
# LISTAR
# ----------------------------

@app.route("/lista")
def lista():

    if "logado" not in session:
        return redirect("/login")

    conn = conectar()
    cursor = conn.cursor()

    cursor.execute(
        "SELECT * FROM hospedes"
    )

    hospedes = cursor.fetchall()

    conn.close()

    return render_template(
        "lista.html",
        hospedes=hospedes
    )

# ----------------------------
# DASHBOARD
# ----------------------------

@app.route("/dashboard")
def dashboard():

    if "logado" not in session:
        return redirect("/login")

    conn = conectar()
    cursor = conn.cursor()

    # ---------------------
    # TOTAL DE HÓSPEDES
    # ---------------------

    cursor.execute(
        "SELECT COUNT(*) FROM hospedes"
    )

    resultado = cursor.fetchone()

    if resultado and resultado[0] is not None:
        total_hospedes = resultado[0]
    else:
        total_hospedes = 0

    # ---------------------
    # FATURAMENTO
    # ---------------------

    cursor.execute(
        "SELECT SUM(total) FROM hospedes"
    )

    resultado = cursor.fetchone()

    if resultado and resultado[0] is not None:
        faturamento = resultado[0]
    else:
        faturamento = 0

    # ---------------------
    # ÚLTIMO HÓSPEDE
    # ---------------------

    cursor.execute(
        "SELECT nome FROM hospedes ORDER BY id DESC LIMIT 1"
    )

    resultado = cursor.fetchone()

    if resultado:
        ultimo_nome = resultado[0]
    else:
        ultimo_nome = "Nenhum"

    # ---------------------
    # DADOS DO GRÁFICO
    # ---------------------

    cursor.execute(
        "SELECT nome, total FROM hospedes"
    )

    dados = cursor.fetchall()

    nomes = []
    valores = []

    for item in dados:

        nomes.append(item[0])
        valores.append(item[1])

    conn.close()

    return render_template(
        "dashboard.html",
        total_hospedes=total_hospedes,
        faturamento=faturamento,
        ultimo_nome=ultimo_nome,
        nomes=nomes,
        valores=valores
    )
# ----------------------------
# CONTROLE DE QUARTOS
# ----------------------------

@app.route("/quartos")
def quartos():

    if "logado" not in session:
        return redirect("/login")

    conn = conectar()
    cursor = conn.cursor()

    hoje = datetime.now().strftime(
        "%Y-%m-%d"
    )

    cursor.execute("""
        SELECT quarto, nome
        FROM hospedes
        WHERE entrada <= ?
        AND saida >= ?
    """, (hoje, hoje))

    ocupados = cursor.fetchall()

    conn.close()

    lista_quartos = [
        "101", "102", "103",
        "104", "105", "106",
        "201", "202", "203"
    ]

    quartos_status = []

    for quarto in lista_quartos:

        status = "Livre"
        hospede = ""

        for item in ocupados:

            if item[0] == quarto:

                status = "Ocupado"
                hospede = item[1]

        quartos_status.append(
            (quarto, status, hospede)
        )

    return render_template(
        "quartos.html",
        quartos=quartos_status
    )

# ----------------------------
# QUARTOS DISPONIVEIS
# ----------------------------

@app.route("/quartos_disponiveis")
def quartos_disponiveis():

    if "logado" not in session:
        return redirect("/login")

    conn = conectar()
    cursor = conn.cursor()

    hoje = datetime.now().strftime(
        "%Y-%m-%d"
    )

    cursor.execute("""
        SELECT quarto
        FROM hospedes
        WHERE entrada <= ?
        AND saida >= ?
    """, (hoje, hoje))

    ocupados = cursor.fetchall()

    conn.close()

    lista_quartos = [
        "101", "102", "103",
        "104", "105", "106",
        "201", "202", "203"
    ]

    livres = []

    for quarto in lista_quartos:

        ocupado = False

        for item in ocupados:

            if item[0] == quarto:
                ocupado = True

        if not ocupado:
            livres.append(quarto)

    return render_template(
        "quartos_disponiveis.html",
        quartos=livres
    )

# ----------------------------
# RESERVAS
# ----------------------------

@app.route("/reservas")
def reservas():

    if "logado" not in session:
        return redirect("/login")

    conn = conectar()
    cursor = conn.cursor()

    # -------------------------
    # BUSCAR HÓSPEDES
    # -------------------------

    cursor.execute("""
        SELECT nome
        FROM hospedes
        ORDER BY nome
    """)

    hospedes = cursor.fetchall()

    # -------------------------
    # BUSCAR RESERVAS
    # -------------------------

    cursor.execute("""
        SELECT id, nome, entrada, saida
        FROM reservas
        ORDER BY id DESC
    """)

    reservas = cursor.fetchall()

    conn.close()

    return render_template(
        "reservas.html",
        hospedes=hospedes,
        reservas=reservas
    )

# ----------------------------
# CHECK-IN DA RESERVA
# ----------------------------

@app.route("/checkin_reserva/<int:id>")
def checkin_reserva(id):

    if "logado" not in session:
        return redirect("/login")

    conn = conectar()
    cursor = conn.cursor()

    cursor.execute(
        "SELECT * FROM reservas WHERE id = ?",
        (id,)
    )

    reserva = cursor.fetchone()

    if reserva:

        nome = reserva[1]
        quarto = reserva[2]
        entrada = reserva[3]
        saida = reserva[4]

        diaria = 100

        from datetime import datetime

        data_entrada = datetime.strptime(
            entrada,
            "%Y-%m-%d"
        )

        data_saida = datetime.strptime(
            saida,
            "%Y-%m-%d"
        )

        dias = (data_saida - data_entrada).days

        total = dias * diaria

        cursor.execute("""
            INSERT INTO hospedes
            (nome, cpf, telefone, quarto,
             entrada, saida, diaria, total)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            nome,
            "-",
            "-",
            quarto,
            entrada,
            saida,
            diaria,
            total
        ))

        cursor.execute(
            "DELETE FROM reservas WHERE id = ?",
            (id,)
        )

        conn.commit()

    conn.close()

    return redirect("/lista")

# ----------------------------
# SALVAR RESERVA
# ----------------------------

@app.route("/salvar_reserva", methods=["POST"])
def salvar_reserva():

    if "logado" not in session:
        return redirect("/login")

    nome = request.form.get("nome")
    quarto = request.form.get("quarto")
    entrada = request.form.get("entrada")
    saida = request.form.get("saida")

    conn = conectar()
    cursor = conn.cursor()

    # Verificar conflito de datas

    cursor.execute("""
        SELECT * FROM reservas
        WHERE quarto = ?
        AND (
            (entrada <= ? AND saida >= ?) OR
            (entrada <= ? AND saida >= ?)
        )
    """, (
        quarto,
        entrada, entrada,
        saida, saida
    ))

    conflito = cursor.fetchone()

    if conflito:

        conn.close()

        return "Quarto já reservado neste período"

    cursor.execute("""
        INSERT INTO reservas
        (nome, quarto, entrada, saida)
        VALUES (?, ?, ?, ?)
    """, (
        nome,
        quarto,
        entrada,
        saida
    ))

    conn.commit()
    conn.close()

    return redirect("/reservas")

# ----------------------------
# CANCELAR RESERVA
# ----------------------------

@app.route("/cancelar_reserva/<int:id>")
def cancelar_reserva(id):

    if "logado" not in session:
        return redirect("/login")

    conn = conectar()
    cursor = conn.cursor()

    cursor.execute(
        "DELETE FROM reservas WHERE id = ?",
        (id,)
    )

    conn.commit()
    conn.close()

    return redirect("/reservas")

# ----------------------------
# RELATORIO PDF
# ----------------------------

@app.route("/relatorio")
def relatorio():

    conn = conectar()
    cursor = conn.cursor()

    cursor.execute(
        "SELECT * FROM hospedes"
    )

    hospedes = cursor.fetchall()

    conn.close()

    caminho_pdf = os.path.join(
        os.getcwd(),
        "relatorio_hospedes.pdf"
    )

    doc = SimpleDocTemplate(
        caminho_pdf
    )

    elementos = []

    estilos = getSampleStyleSheet()

    titulo = Paragraph(
        "Relatório de Hóspedes",
        estilos["Title"]
    )

    elementos.append(titulo)

    dados = [
        ["ID", "Nome", "Quarto", "Total"]
    ]

    for h in hospedes:

        dados.append([
            h[0],
            h[1],
            h[4],
            h[8]
        ])

    tabela = Table(dados)

    estilo = TableStyle([
        ("GRID", (0, 0), (-1, -1), 1, colors.black)
    ])

    tabela.setStyle(estilo)

    elementos.append(tabela)

    doc.build(elementos)

    return send_file(
        caminho_pdf,
        as_attachment=True
    )

# ----------------------------
# LOGOUT
# ----------------------------

@app.route("/logout")
def logout():

    session.clear()

    return redirect("/login")

# ----------------------------
# EXECUTAR
# ----------------------------

if __name__ == "__main__":

    app.run(debug=True)