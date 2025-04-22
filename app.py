from flask import Flask, render_template, request, redirect, url_for
import sqlite3
import re

app = Flask(__name__)

# Inicializa o banco se não existir
def init_db():
    produtos = '''
        CREATE TABLE IF NOT EXISTS produtos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome TEXT NOT NULL,
            quantidade INTEGER NOT NULL,
            valor DECIMAL(2,2) NOT NULL,
            custo DECIMAL(2,2) NOT NULL
        )
    '''
    vendas = '''
        CREATE TABLE IF NOT EXISTS vendas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            produto_id INTEGER,
            quantidade INTEGER,
            valor_total REAL,
            data TEXT DEFAULT CURRENT_DATE,
            FOREIGN KEY(produto_id) REFERENCES produtos(id)
        )
        '''
    conn = sqlite3.connect('banco.db')
    c = conn.cursor()
    c.execute(produtos)
    conn.commit()
    conn.close()

    conn = sqlite3.connect('banco.db')
    c = conn.cursor()
    c.execute(vendas)
    conn.commit()
    conn.close()


#AÇÕES PARA PRODUTOS
@app.route('/')
def index():
    conn = sqlite3.connect('banco.db')
    c = conn.cursor()
    c.execute('SELECT * FROM produtos')
    produtos = c.fetchall()
    conn.close()
    return render_template('index.html', produtos=produtos)


@app.route('/adicionar', methods=['POST'])
def adicionar():
    nome = request.form['nome']
    quantidade = request.form['quantidade']
    valor = float(request.form['valor'].replace(",", "."))
    custo = float(request.form['custo'].replace(",", "."))

    conn = sqlite3.connect('banco.db')
    c = conn.cursor()
    c.execute("INSERT INTO produtos (nome, quantidade, custo, valor) VALUES (?, ?, ?, ?)",
               (nome, quantidade, custo, valor))
    conn.commit()
    conn.close()
    return redirect('/')




@app.route('/editar/<int:id>', methods=['GET', 'POST'])
def editar(id):
    conn = sqlite3.connect('banco.db')
    c = conn.cursor()

    if request.method == 'POST':
        nome = request.form['nome']
        quantidade = int(request.form['quantidade'])
        valor = float(request.form['valor'].replace(",", "."))
        custo = float(request.form['custo'].replace(",", "."))
        print(nome)
        c.execute('UPDATE produtos SET nome = ?, quantidade = ?, custo = ?, valor = ? WHERE id = ?', (nome, quantidade, custo, valor, id))
        conn.commit()
        conn.close()
        return redirect('/')

    c.execute('SELECT * FROM produtos WHERE id = ?', (id,))
    produto = c.fetchone()
    conn.close()

    if produto is None:
        return "Produto não encontrado", 404

    return render_template('editar.html', produto=produto)


#DELETE DE LINHAS
@app.route('/deletar_produto/<int:id>')
def deletar_produto(id):
    conn = sqlite3.connect('banco.db')
    c = conn.cursor()
    c.execute('DELETE FROM produtos WHERE id = ?', (id,))
    conn.commit()
    conn.close()
    return redirect('/')

@app.route("/deletar_venda/<int:id>")
def deletar_venda(id):
    conn = sqlite3.connect('banco.db')
    cur = conn.cursor()
    cur.execute("DELETE FROM vendas WHERE id = ?", (id,))
    conn.commit()
    conn.close()
    return redirect(url_for('historico'))


#AÇÕES PARA VENDAS
@app.route('/vender/<int:produto_id>', methods=['GET', 'POST'])
def vender(produto_id):
    con = sqlite3.connect('banco.db')
    cur = con.cursor()

    if request.method == 'POST':
        quantidade_vendida = int(request.form['quantidade'])

        # Pega estoque e valor do produto
        cur.execute('SELECT quantidade, valor FROM produtos WHERE id=?', (produto_id,))
        produto = cur.fetchone()

        if produto:
            estoque_atual, valor_unitario = produto

            if quantidade_vendida <= estoque_atual:
                novo_estoque = estoque_atual - quantidade_vendida
                valor_total = quantidade_vendida * valor_unitario
                print("venda realizada")
                # Atualiza estoque
                cur.execute('UPDATE produtos SET quantidade=? WHERE id=?', (novo_estoque, produto_id))

                # Registra a venda
                cur.execute('INSERT INTO vendas (produto_id, quantidade, valor_total) VALUES (?, ?, ?)',
                            (produto_id, quantidade_vendida, valor_total))

                con.commit()
                con.close()
                return redirect(url_for('index'))
            else:
                con.close()
                return "Estoque insuficiente"
        else:
            con.close()
            return "Produto não encontrado"

    # Se GET, exibe formulário
    cur.execute('SELECT nome FROM produtos WHERE id=?', (produto_id,))
    produto = cur.fetchone()
    cur.execute("SELECT * FROM vendas WHERE produto_id = ?", (produto_id,))
    vendas = cur.fetchall()
    con.close()
    return render_template('vender.html', produto=produto, vendas=vendas)


#pagina de historico 
@app.route("/historico")
def historico():
    query = '''
    SELECT vendas.id, produtos.nome, vendas.quantidade,
           produtos.valor, 
           vendas.valor_total, 
           vendas.data
    FROM vendas JOIN produtos ON vendas.produto_id = produtos.id'''
    conn = sqlite3.connect('banco.db')
    cur = conn.cursor()
    cur.execute(query)
    vendas = cur.fetchall()
    conn.close()
    labels, dados, liquido_vendas = calculo_liquido()
    lucro_est = est_lucro()
    return render_template("historico.html",
                           vendas=vendas,
                           labels=labels,
                           dados=dados,
                           liquido_vendas=liquido_vendas,
                           lucro_est=lucro_est)

def calculo_liquido():
    query = '''
    SELECT 
    p.nome,
    ROUND(IFNULL(SUM(v.quantidade * p.valor), 0) - (p.quantidade * p.custo), 2) as liquido
    FROM produtos p
    LEFT JOIN vendas v ON v.produto_id = p.id
    GROUP BY p.id
    ORDER BY liquido DESC;'''
    conn = sqlite3.connect('banco.db')
    cur = conn.cursor()
    cur.execute(query)
    vendas = cur.fetchall()
    print(vendas)
    labels = [v[0] for v in vendas]
    dados = [round(v[1], 2) for v in vendas]
    liquido_vendas = sum(dados) 

    return  labels, dados, liquido_vendas

def est_lucro():
    query = '''
    SELECT SUM((valor * quantidade) - (custo * quantidade)) 
    FROM  produtos'''
    conn = sqlite3.connect('banco.db')
    cur = conn.cursor()
    cur.execute(query)
    valor = cur.fetchall()[0][0]

    return valor

    


if __name__ == '__main__':
    init_db()
    #↓ Rodar apenas na maquina local ↓
    app.run(debug=True)
    #↓ Rodar no mini-server ↓
    #app.run(host='0.0.0.0', port=5000, debug=True)
