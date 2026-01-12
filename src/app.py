import os
from flask import Flask, render_template, request, jsonify, session, redirect, url_for
import psycopg2
from psycopg2 import extras
from datetime import datetime, date
from decimal import Decimal

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'mercado_secret_key_123')

# Configuração do Banco de Dados (Render usa DATABASE_URL)
DATABASE_URL = os.environ.get('DATABASE_URL')

def get_db_connection():
    return psycopg2.connect(DATABASE_URL)

def formatar_data_br(dt):
    if isinstance(dt, (date, datetime)):
        return dt.strftime('%d/%m/%Y')
    return dt

@app.route('/')
def index():
    if 'usuario_id' not in session:
        return redirect(url_for('login'))
    return render_template('index.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        usuario = request.form.get('usuario')
        senha = request.form.get('senha')
        
        with get_db_connection() as conn:
            with conn.cursor(cursor_factory=extras.DictCursor) as cursor:
                cursor.execute("SELECT * FROM usuarios WHERE usuario = %s AND senha = %s", (usuario, senha))
                user = cursor.fetchone()
                if user:
                    session['usuario_id'] = user['id']
                    session['usuario_nome'] = user['nome']
                    return redirect(url_for('index'))
        return render_template('login.html', error="Usuário ou senha inválidos")
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

# --- APIs de Produtos ---

@app.route('/api/produtos', methods=['GET'])
def listar_produtos():
    with get_db_connection() as conn:
        with conn.cursor(cursor_factory=extras.DictCursor) as cursor:
            cursor.execute("SELECT * FROM produtos ORDER BY descricao ASC")
            produtos = [dict(row) for row in cursor.fetchall()]
            for p in produtos:
                p['validade'] = formatar_data_br(p['validade'])
                p['preco'] = float(p['preco'])
    return jsonify(produtos)

@app.route('/api/produtos/buscar/<ean>')
def buscar_produto(ean):
    with get_db_connection() as conn:
        with conn.cursor(cursor_factory=extras.DictCursor) as cursor:
            cursor.execute("SELECT * FROM produtos WHERE ean = %s", (ean,))
            produto = cursor.fetchone()
            if produto:
                p = dict(produto)
                p['validade'] = p['validade'].isoformat() if p['validade'] else None
                p['preco'] = float(p['preco'])
                return jsonify({"success": True, "produto": p})
    return jsonify({"success": False, "message": "Produto não encontrado"})

@app.route('/api/produtos/cadastrar', methods=['POST'])
def cadastrar_produto():
    data = request.json
    ean = data.get('ean')
    descricao = data.get('descricao')
    preco = data.get('preco', 0)
    validade = data.get('validade')
    quantidade = data.get('quantidade', 0)

    try:
        with get_db_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute("""
                    INSERT INTO produtos (ean, descricao, preco, validade, quantidade)
                    VALUES (%s, %s, %s, %s, %s)
                    ON CONFLICT (ean) DO UPDATE SET
                        descricao = EXCLUDED.descricao,
                        preco = EXCLUDED.preco,
                        validade = EXCLUDED.validade,
                        quantidade = produtos.quantidade + EXCLUDED.quantidade,
                        ultima_atualizacao = CURRENT_TIMESTAMP
                    RETURNING id
                """, (ean, descricao, preco, validade, quantidade))
                produto_id = cursor.fetchone()[0]
                
                # Registrar movimentação inicial se houver quantidade
                if int(quantidade) > 0:
                    cursor.execute("""
                        INSERT INTO movimentacoes (produto_id, tipo, quantidade, usuario_id, observacao)
                        VALUES (%s, 'ENTRADA', %s, %s, 'Cadastro Inicial')
                    """, (produto_id, quantidade, session.get('usuario_id')))
                
                conn.commit()
        return jsonify({"success": True, "message": "Produto cadastrado/atualizado com sucesso"})
    except Exception as e:
        return jsonify({"success": False, "message": str(e)})

@app.route('/api/movimentar', methods=['POST'])
def movimentar_estoque():
    data = request.json
    ean = data.get('ean')
    tipo = data.get('tipo') # 'ENTRADA' ou 'SAIDA'
    qtd = int(data.get('quantidade', 0))
    
    try:
        with get_db_connection() as conn:
            with conn.cursor(cursor_factory=extras.DictCursor) as cursor:
                cursor.execute("SELECT id, quantidade FROM produtos WHERE ean = %s", (ean,))
                prod = cursor.fetchone()
                if not prod:
                    return jsonify({"success": False, "message": "Produto não encontrado"})
                
                nova_qtd = prod['quantidade'] + qtd if tipo == 'ENTRADA' else prod['quantidade'] - qtd
                if nova_qtd < 0:
                    return jsonify({"success": False, "message": "Estoque insuficiente"})
                
                cursor.execute("UPDATE produtos SET quantidade = %s, ultima_atualizacao = CURRENT_TIMESTAMP WHERE id = %s", (nova_qtd, prod['id']))
                cursor.execute("""
                    INSERT INTO movimentacoes (produto_id, tipo, quantidade, usuario_id)
                    VALUES (%s, %s, %s, %s)
                """, (prod['id'], tipo, qtd, session.get('usuario_id')))
                
                conn.commit()
        return jsonify({"success": True, "nova_quantidade": nova_qtd})
    except Exception as e:
        return jsonify({"success": False, "message": str(e)})

@app.route('/api/movimentacoes/hoje')
def movimentacoes_hoje():
    with get_db_connection() as conn:
        with conn.cursor(cursor_factory=extras.DictCursor) as cursor:
            cursor.execute("""
                SELECT m.*, p.descricao, p.ean, u.nome as usuario_nome
                FROM movimentacoes m
                JOIN produtos p ON m.produto_id = p.id
                JOIN usuarios u ON m.usuario_id = u.id
                WHERE m.data_movimentacao::date = CURRENT_DATE
                ORDER BY m.data_movimentacao DESC
            """)
            movs = [dict(row) for row in cursor.fetchall()]
            for m in movs:
                m['data_movimentacao'] = m['data_movimentacao'].strftime('%H:%M:%S')
    return jsonify(movs)

if __name__ == '__main__':
    app.run(debug=True)
