# Importações necessárias do Flask e bibliotecas auxiliares
from flask import Flask, render_template, request, redirect, url_for, flash, session, abort
from flask_login import LoginManager, login_user, login_required, logout_user, UserMixin, current_user
import mysql.connector
import os
from datetime import date, timedelta
from functools import wraps
 
# Instanciação do app Flask e configuração da chave secreta para sessões
app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'chave-dev-local')

# --- CONSTANTES DA APLICAÇÃO ---
VALOR_MULTA_DIARIA = 0.50 # Define o valor da multa por dia de atraso

# Configuração do gerenciador de login do Flask-Login
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'
login_manager.login_message = "Por favor, faça o login para acessar esta página."
login_manager.login_message_category = "info"

# --- CONFIGURAÇÃO DO BANCO DE DADOS ---
def conectar():
    """Estabelece conexão com o banco de dados MySQL hospedado no Railway."""
    return mysql.connector.connect(
        host=os.environ.get('MYSQLHOST'),         # Endereço fornecido pelo Railway
        user=os.environ.get('MYSQLUSER'),         # Usuário (geralmente root)
        password=os.environ.get('MYSQLPASSWORD'), # Sua senha do Railway
        database=os.environ.get('MYSQLDATABASE'), # Nome do banco (geralmente railway)
        port=int(os.environ.get('MYSQLPORT')) # Porta de conexão
    )

# --- MODELOS DE USUÁRIO E AUTENTICAÇÃO ---
class FuncionarioUser(UserMixin):
    def __init__(self, id_funcionario, nome):
        self.id = id_funcionario
        self.nome = nome
        self.role = 'admin' # Adiciona o perfil de admin

    def get_id(self):
        return f"funcionario-{self.id}"

class UsuarioUser(UserMixin):
    def __init__(self, cpf, nome):
        self.id = cpf
        self.nome = nome
        self.role = 'usuario' # Adiciona o perfil de usuário

    def get_id(self):
        return f"usuario-{self.id}"

@login_manager.user_loader
def load_user(user_id_str):
    try:
        tipo, user_id = user_id_str.split('-', 1)
        conn = conectar()
        cursor = conn.cursor(dictionary=True)
        
        if tipo == 'funcionario':
            cursor.execute("SELECT ID_funcionario, nome FROM Funcionario WHERE ID_funcionario = %s", (user_id,))
            func = cursor.fetchone()
            if func:
                return FuncionarioUser(func['ID_funcionario'], func['nome'])
        elif tipo == 'usuario':
            cursor.execute("SELECT CPF, nome FROM Usuario WHERE CPF = %s", (user_id,))
            user = cursor.fetchone()
            if user:
                return UsuarioUser(user['CPF'], user['nome'])
    except Exception as e:
        print(f"Erro ao carregar usuário: {e}")
        return None
    finally:
        if 'conn' in locals() and conn.is_connected():
            conn.close()
    return None

# --- DECORADOR PARA VERIFICAR PERMISSÃO DE ADMIN ---
def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or current_user.role != 'admin':
            flash("Acesso negado. Esta área é restrita para administradores.", "danger")
            return redirect(url_for('portal_acervo_publico'))
        return f(*args, **kwargs)
    return decorated_function

# --- ROTAS DE AUTENTICAÇÃO E PÚBLICAS ---
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        senha = request.form['senha']
        conn = conectar()
        cursor = conn.cursor(dictionary=True)

        # Tenta fazer login como funcionário
        cursor.execute("SELECT * FROM Funcionario WHERE email = %s", (email,))
        func = cursor.fetchone()
        if func and func['senha'] == senha:
            user = FuncionarioUser(func['ID_funcionario'], func['nome'])
            login_user(user)
            conn.close()
            return redirect(url_for('index'))

        # Se não for funcionário, tenta como usuário
        cursor.execute("SELECT * FROM Usuario WHERE email = %s", (email,))
        user_comum = cursor.fetchone()
        conn.close()
        if user_comum and user_comum['senha'] == senha:
            user = UsuarioUser(user_comum['CPF'], user_comum['nome'])
            login_user(user)
            return redirect(url_for('portal_acervo_publico'))

        flash('Credenciais inválidas. Verifique seu e-mail e senha.', 'danger')
            
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Você foi desconectado.', 'info')
    return redirect(url_for('login'))

# --- ROTAS DO PAINEL DE ADMIN ---
@app.route('/')
@login_required
@admin_required
def index():
    conn = conectar()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute("SELECT COUNT(*) as total FROM Usuario")
        total_usuarios = cursor.fetchone()['total']
        cursor.execute("SELECT COUNT(*) as total FROM Item_acervo")
        total_itens = cursor.fetchone()['total']
        cursor.execute("SELECT COUNT(*) as total FROM Emprestimo WHERE status = 'Ativo'")
        emprestimos_ativos = cursor.fetchone()['total']
        return render_template('index.html', total_usuarios=total_usuarios, total_itens=total_itens, emprestimos_ativos=emprestimos_ativos)
    except Exception as e:
        flash(f"Erro ao carregar estatísticas: {str(e)}", "danger")
        return render_template('index.html')
    finally:
        conn.close()

# --- ROTAS DO PORTAL DO USUÁRIO ---
@app.route('/portal/acervo')
@login_required
def portal_acervo_publico():
    conn = conectar()
    cursor = conn.cursor(dictionary=True)
    try:
        termo_busca = request.args.get('busca', '')
        query = "SELECT * FROM Item_acervo WHERE titulo LIKE %s"
        cursor.execute(query, (f'%{termo_busca}%',))
        itens = cursor.fetchall()
        return render_template('portal_acervo.html', itens=itens, termo_busca=termo_busca)
    except Exception as e:
        flash(f"Erro ao carregar o acervo: {e}", "danger")
        return render_template('portal_acervo.html', itens=[])
    finally:
        conn.close()

@app.route('/portal/meus_emprestimos')
@login_required
def portal_meus_emprestimos():
    if current_user.role != 'usuario':
        return abort(403)
    
    conn = conectar()
    cursor = conn.cursor(dictionary=True)
    try:
        query = """
            SELECT E.data_emprest, E.data_dev, E.status, E.multa, I.titulo
            FROM Emprestimo E
            JOIN Movimentacao M ON E.ID_emprestimo = M.ID_emprestimo
            JOIN Item_acervo I ON M.ID_item = I.ID_item
            WHERE E.CPF = %s AND M.tipo = 'Emprestado'
            ORDER BY E.data_emprest DESC
        """
        cursor.execute(query, (current_user.id,))
        emprestimos = cursor.fetchall()
        return render_template('portal_meus_emprestimos.html', emprestimos=emprestimos)
    except Exception as e:
        flash(f"Erro ao carregar seus empréstimos: {e}", "danger")
        return render_template('portal_meus_emprestimos.html', emprestimos=[])
    finally:
        conn.close()

# --- CRUD DE FUNCIONÁRIOS ---
@app.route('/funcionarios', methods=['GET', 'POST'])
@login_required
@admin_required
def funcionarios():
    conn = conectar()
    cursor = conn.cursor(dictionary=True)
    try:
        if request.method == 'POST':
            nome = request.form['nome']
            cargo = request.form['cargo']
            telefone = request.form.get('telefone')
            email = request.form['email']
            cpf = request.form['cpf']
            senha = request.form['senha']

            cursor.execute("INSERT INTO Funcionario (nome, cargo, telefone, email, CPF, senha) VALUES (%s, %s, %s, %s, %s, %s)",
                           (nome, cargo, telefone, email, cpf, senha))
            conn.commit()
            flash('Funcionário cadastrado com sucesso!', 'success')
            return redirect(url_for('funcionarios'))
        
        cursor.execute("SELECT * FROM Funcionario")
        lista_funcionarios = cursor.fetchall()
        return render_template('funcionarios.html', funcionarios=lista_funcionarios)
    except Exception as e:
        conn.rollback() 
        flash(f'Falha ao processar a página de funcionários. Erro: {e}', 'danger')
        return redirect(url_for('index'))
    finally:
        conn.close()

@app.route('/funcionarios/editar/<int:id_funcionario>', methods=['GET', 'POST'])
@login_required
@admin_required
def editar_funcionario(id_funcionario):
    conn = conectar()
    cursor = conn.cursor(dictionary=True)
    try:
        if request.method == 'POST':
            nome = request.form['nome']
            cargo = request.form['cargo']
            telefone = request.form.get('telefone')
            email = request.form['email']
            cpf = request.form['cpf']
            
            cursor.execute("UPDATE Funcionario SET nome=%s, cargo=%s, telefone=%s, email=%s, CPF=%s WHERE ID_funcionario=%s",
                           (nome, cargo, telefone, email, cpf, id_funcionario))
            conn.commit()
            flash('Funcionário atualizado com sucesso!', 'success')
            return redirect(url_for('funcionarios'))
        
        cursor.execute("SELECT * FROM Funcionario WHERE ID_funcionario = %s", (id_funcionario,))
        funcionario = cursor.fetchone()
        if not funcionario:
            flash('Funcionário não encontrado.', 'danger')
            return redirect(url_for('funcionarios'))
        return render_template('editar_funcionario.html', funcionario=funcionario)
    except Exception as e:
        flash(f'Erro ao editar funcionário: {e}', 'danger')
        return redirect(url_for('funcionarios'))
    finally:
        conn.close()

@app.route('/funcionarios/excluir/<int:id_funcionario>', methods=['POST'])
@login_required
@admin_required
def excluir_funcionario(id_funcionario):
    conn = conectar()
    cursor = conn.cursor()
    try:
        cursor.execute("DELETE FROM Funcionario WHERE ID_funcionario = %s", (id_funcionario,))
        conn.commit()
        flash('Funcionário excluído com sucesso!', 'success')
    except Exception as e:
        conn.rollback()
        flash(f'Erro ao excluir funcionário. Verifique se ele não está associado a outras operações. Erro: {e}', 'danger')
    finally:
        conn.close()
    return redirect(url_for('funcionarios'))


# --- CRUD DE USUÁRIOS ---
@app.route('/usuarios', methods=['GET', 'POST'])
@login_required
@admin_required
def usuarios():
    conn = conectar()
    cursor = conn.cursor(dictionary=True)
    try:
        if request.method == 'POST':
            cpf = request.form['cpf']
            nome = request.form['nome']
            telefone = request.form.get('telefone')
            email = request.form['email']
            limite = request.form['limite_emprestimo']
            senha = request.form['senha']

            cursor.execute("INSERT INTO Usuario (CPF, nome, telefone, email, limite_emprestimo, senha) VALUES (%s, %s, %s, %s, %s, %s)",
                           (cpf, nome, telefone, email, limite, senha))
            conn.commit()
            flash('Usuário cadastrado com sucesso!', 'success')
            return redirect(url_for('usuarios'))

        cursor.execute("SELECT * FROM Usuario")
        lista_usuarios = cursor.fetchall()
        return render_template('usuarios.html', usuarios=lista_usuarios)
    except Exception as e:
        conn.rollback()
        flash(f'Falha ao processar a página de usuários. Erro: {e}', 'danger')
        return redirect(url_for('index'))
    finally:
        conn.close()

@app.route('/usuarios/editar/<cpf>', methods=['GET', 'POST'])
@login_required
@admin_required
def editar_usuario(cpf):
    conn = conectar()
    cursor = conn.cursor(dictionary=True)
    try:
        if request.method == 'POST':
            nome = request.form['nome']
            telefone = request.form.get('telefone')
            email = request.form['email']
            limite = request.form['limite_emprestimo']
            cursor.execute("UPDATE Usuario SET nome=%s, telefone=%s, email=%s, limite_emprestimo=%s WHERE CPF=%s",
                           (nome, telefone, email, limite, cpf))
            conn.commit()
            flash('Usuário atualizado com sucesso!', 'success')
            return redirect(url_for('usuarios'))
        
        cursor.execute("SELECT * FROM Usuario WHERE CPF = %s", (cpf,))
        usuario = cursor.fetchone()
        return render_template('editar_usuario.html', usuario=usuario)
    except Exception as e:
        flash(f'Erro ao editar usuário: {e}', 'danger')
        return redirect(url_for('usuarios'))
    finally:
        conn.close()

@app.route('/usuarios/excluir/<cpf>', methods=['POST'])
@login_required
@admin_required
def excluir_usuario(cpf):
    conn = conectar()
    cursor = conn.cursor()
    try:
        cursor.execute("DELETE FROM Usuario WHERE CPF = %s", (cpf,))
        conn.commit()
        flash('Usuário excluído com sucesso!', 'success')
    except Exception as e:
        conn.rollback()
        flash(f'Erro ao excluir usuário. Verifique se ele não possui empréstimos ativos. Erro: {e}', 'danger')
    finally:
        conn.close()
    return redirect(url_for('usuarios'))

# --- CRUD DE ITENS DO ACERVO ---
@app.route('/itens', methods=['GET', 'POST'])
@login_required
@admin_required
def itens():
    conn = conectar()
    cursor = conn.cursor(dictionary=True)
    try:
        if request.method == 'POST':
            titulo = request.form['titulo']
            autor = request.form['autor']
            ano = request.form.get('ano') or None
            tipo_item = request.form['tipo_item']
            status_item = request.form['status_item']
            
            cursor.execute("INSERT INTO Item_acervo (titulo, autor, ano, tipo_item, status_item, ID_funcionario) VALUES (%s, %s, %s, %s, %s, %s)",
                           (titulo, autor, ano, tipo_item, status_item, current_user.id))
            conn.commit()
            flash('Item cadastrado com sucesso!', 'success')
            return redirect(url_for('itens'))

        cursor.execute("SELECT I.*, F.nome AS funcionario_nome FROM Item_acervo I JOIN Funcionario F ON I.ID_funcionario = F.ID_funcionario")
        lista_itens = cursor.fetchall()
        
        cursor.execute("SELECT CPF, nome FROM Usuario")
        lista_usuarios = cursor.fetchall()

        return render_template('itens.html', itens=lista_itens, usuarios=lista_usuarios)
    except Exception as e:
        flash(f'Erro na página de itens: {e}', 'danger')
        return redirect(url_for('index'))
    finally:
        conn.close()

@app.route('/itens/editar/<int:id_item>', methods=['GET', 'POST'])
@login_required
@admin_required
def editar_item(id_item):
    conn = conectar()
    cursor = conn.cursor(dictionary=True)
    try:
        if request.method == 'POST':
            titulo = request.form['titulo']
            autor = request.form['autor']
            ano = request.form.get('ano') or None
            tipo_item = request.form['tipo_item']
            status_item = request.form['status_item']
            cursor.execute("UPDATE Item_acervo SET titulo=%s, autor=%s, ano=%s, tipo_item=%s, status_item=%s WHERE ID_item=%s",
                           (titulo, autor, ano, tipo_item, status_item, id_item))
            conn.commit()
            flash('Item atualizado com sucesso!', 'success')
            return redirect(url_for('itens'))
        
        cursor.execute("SELECT * FROM Item_acervo WHERE ID_item = %s", (id_item,))
        item = cursor.fetchone()
        return render_template('editar_item.html', item=item)
    except Exception as e:
        flash(f'Erro ao editar item: {e}', 'danger')
        return redirect(url_for('itens'))
    finally:
        conn.close()

@app.route('/itens/excluir/<int:id_item>', methods=['POST'])
@login_required
@admin_required
def excluir_item(id_item):
    conn = conectar()
    cursor = conn.cursor()
    try:
        cursor.execute("DELETE FROM Item_acervo WHERE ID_item = %s", (id_item,))
        conn.commit()
        flash('Item excluído com sucesso!', 'success')
    except Exception as e:
        conn.rollback()
        flash(f'Erro ao excluir item. Verifique se ele não está em um empréstimo ou reserva. Erro: {e}', 'danger')
    finally:
        conn.close()
    return redirect(url_for('itens'))

# --- ROTA DE EMPRÉSTIMOS (ATUALIZADA) ---
@app.route('/emprestimos', methods=['GET', 'POST'])
@login_required
@admin_required
def emprestimos():
    conn = conectar()
    if not conn:
        flash('Erro de conexão com o servidor.', 'danger')
        return redirect(url_for('index'))
    
    cursor = conn.cursor(dictionary=True)
    try:
        if request.method == 'POST':
            data_emprest = request.form['data_emprest']
            data_dev = request.form['data_dev']
            cpf_usuario = request.form['cpf_usuario']
            itens_selecionados = request.form.getlist('itens_selecionados')

            if not itens_selecionados:
                flash('Você deve selecionar pelo menos um item para o empréstimo.', 'warning')
                return redirect(url_for('emprestimos'))

            cursor.execute("SELECT limite_emprestimo FROM Usuario WHERE CPF = %s", (cpf_usuario,))
            user_data = cursor.fetchone()
            if not user_data:
                flash('Usuário não encontrado.', 'danger')
                return redirect(url_for('emprestimos'))
            limite_usuario = user_data['limite_emprestimo']

            query_ativos = """
                SELECT COUNT(M.ID_item) as total_ativos
                FROM Emprestimo E
                JOIN Movimentacao M ON E.ID_emprestimo = M.ID_emprestimo
                WHERE E.CPF = %s AND E.status = 'Ativo' AND M.tipo = 'Emprestado'
            """
            cursor.execute(query_ativos, (cpf_usuario,))
            resultado_ativos = cursor.fetchone()
            itens_ativos = resultado_ativos['total_ativos'] if resultado_ativos else 0

            if (itens_ativos + len(itens_selecionados)) > limite_usuario:
                flash(f'Operação falhou: O usuário já possui {itens_ativos} itens. Limite de {limite_usuario} excedido.', 'danger')
                return redirect(url_for('emprestimos'))
            
            cursor.execute("INSERT INTO Emprestimo (data_emprest, data_dev, status, ID_funcionario, CPF) VALUES (%s, %s, %s, %s, %s)",
                           (data_emprest, data_dev, 'Ativo', current_user.id, cpf_usuario))
            id_emprestimo = cursor.lastrowid

            for item_id in itens_selecionados:
                cursor.execute("INSERT INTO Movimentacao (ID_emprestimo, ID_item, tipo, data_movimentacao) VALUES (%s, %s, %s, %s)",
                               (id_emprestimo, item_id, 'Emprestado', data_emprest))
                cursor.execute("UPDATE Item_acervo SET status_item = 'Emprestado' WHERE ID_item = %s", (item_id,))
                # Atualiza a reserva para 'Concluída' caso exista uma reserva aguardando retirada para este item
                cursor.execute("UPDATE Reserva SET status_reserva = 'Concluída' WHERE ID_item = %s AND status_reserva = 'Aguardando Retirada'", (item_id,))
            
            conn.commit()
            flash('Empréstimo registrado com sucesso!', 'success')
            return redirect(url_for('emprestimos'))

        # --- LÓGICA GET ATUALIZADA PARA BUSCA ---
        termo_busca = request.args.get('busca', '')
        cpf_selecionado = request.args.get('cpf_usuario', '')
        data_emprest_selecionada = request.args.get('data_emprest', '')
        data_dev_selecionada = request.args.get('data_dev', '')

        cursor.execute("SELECT E.*, U.nome AS usuario_nome FROM Emprestimo E JOIN Usuario U ON E.CPF = U.CPF ORDER BY E.data_emprest DESC")
        lista_emprestimos = cursor.fetchall()
        
        cursor.execute("SELECT CPF, nome FROM Usuario")
        lista_usuarios = cursor.fetchall()

        query_itens = "SELECT ID_item, titulo FROM Item_acervo WHERE (status_item = 'Disponível' OR status_item = 'Reservado')"
        params = []
        if termo_busca:
            query_itens += " AND titulo LIKE %s"
            params.append(f'%{termo_busca}%')
        
        cursor.execute(query_itens, params)
        lista_itens_disponiveis = cursor.fetchall()

        return render_template('emprestimos.html', 
                               emprestimos=lista_emprestimos, 
                               usuarios=lista_usuarios, 
                               itens_disponiveis=lista_itens_disponiveis,
                               termo_busca=termo_busca,
                               cpf_selecionado=cpf_selecionado,
                               data_emprest_selecionada=data_emprest_selecionada,
                               data_dev_selecionada=data_dev_selecionada)
    except Exception as e:
        if conn.is_connected():
            conn.rollback()
        flash(f'Erro na página de empréstimos: {e}', 'danger')
        return redirect(url_for('index'))
    finally:
        if conn.is_connected():
            conn.close()

@app.route('/emprestimos/editar/<int:id_emprestimo>', methods=['GET', 'POST'])
@login_required
@admin_required
def editar_emprestimo(id_emprestimo):
    conn = conectar()
    cursor = conn.cursor(dictionary=True)
    try:
        if request.method == 'POST':
            data_emprest = request.form['data_emprest']
            data_dev = request.form['data_dev']
            status = request.form['status']
            multa = request.form.get('multa', 0.0)
            
            cursor.execute("UPDATE Emprestimo SET data_emprest=%s, data_dev=%s, status=%s, multa=%s WHERE ID_emprestimo=%s",
                           (data_emprest, data_dev, status, multa, id_emprestimo))
            conn.commit()
            flash('Empréstimo atualizado com sucesso!', 'success')
            return redirect(url_for('emprestimos'))

        cursor.execute("SELECT E.*, F.nome AS funcionario_nome, U.nome AS usuario_nome FROM Emprestimo E JOIN Funcionario F ON E.ID_funcionario = F.ID_funcionario JOIN Usuario U ON E.CPF = U.CPF WHERE E.ID_emprestimo = %s", (id_emprestimo,))
        emprestimo = cursor.fetchone()

        cursor.execute("SELECT I.ID_item, I.titulo FROM Movimentacao M JOIN Item_acervo I ON M.ID_item = I.ID_item WHERE M.ID_emprestimo = %s", (id_emprestimo,))
        itens_emprestimo = cursor.fetchall()

        if not emprestimo:
            flash('Empréstimo não encontrado.', 'danger')
            return redirect(url_for('emprestimos'))

        return render_template('editar_emprestimo.html', emprestimo=emprestimo, itens_emprestimo=itens_emprestimo)
    except Exception as e:
        flash(f'Erro ao editar empréstimo: {e}', 'danger')
        return redirect(url_for('emprestimos'))
    finally:
        conn.close()


@app.route('/emprestimos/devolver/<int:id_emprestimo>', methods=['POST'])
@login_required
@admin_required
def devolver_emprestimo(id_emprestimo):
    conn = conectar()
    cursor = conn.cursor(dictionary=True)
    try:
        data_devolucao = date.today()
        
        cursor.execute("SELECT data_dev FROM Emprestimo WHERE ID_emprestimo = %s", (id_emprestimo,))
        emprestimo_data = cursor.fetchone()
        data_prevista_dev = emprestimo_data['data_dev']

        multa_calculada = 0.0
        if data_devolucao > data_prevista_dev:
            dias_atraso = (data_devolucao - data_prevista_dev).days
            multa_calculada = dias_atraso * VALOR_MULTA_DIARIA
            flash(f'Multa por atraso de {dias_atraso} dias aplicada: R$ {multa_calculada:.2f}', 'warning')

        cursor.execute("UPDATE Emprestimo SET status = 'Finalizado', data_dev_real = %s, multa = %s WHERE ID_emprestimo = %s",
                       (data_devolucao.isoformat(), multa_calculada, id_emprestimo))

        cursor.execute("SELECT ID_item FROM Movimentacao WHERE ID_emprestimo = %s AND tipo = 'Emprestado'", (id_emprestimo,))
        itens_devolvidos = cursor.fetchall()

        for item in itens_devolvidos:
            item_id = item['ID_item']
            
            cursor.execute("""
                INSERT INTO Movimentacao (ID_emprestimo, ID_item, tipo, data_movimentacao)
                VALUES (%s, %s, %s, %s)
                ON DUPLICATE KEY UPDATE
                    tipo = VALUES(tipo),
                    data_movimentacao = VALUES(data_movimentacao)
            """, (id_emprestimo, item_id, 'Devolvido', data_devolucao.isoformat()))
            
            cursor.execute("SELECT ID_reserva FROM Reserva WHERE ID_item = %s AND status_reserva = 'Ativa' ORDER BY data_reserva ASC LIMIT 1", (item_id,))
            reserva_ativa = cursor.fetchone()
            
            if reserva_ativa:
                cursor.execute("UPDATE Item_acervo SET status_item = 'Reservado' WHERE ID_item = %s", (item_id,))
                data_limite = data_devolucao + timedelta(days=7)
                cursor.execute("UPDATE Reserva SET status_reserva = 'Aguardando Retirada', data_limite_retirada = %s WHERE ID_reserva = %s",
                               (data_limite.isoformat(), reserva_ativa['ID_reserva']))
            else:
                cursor.execute("UPDATE Item_acervo SET status_item = 'Disponível' WHERE ID_item = %s", (item_id,))
        
        conn.commit()
        flash('Devolução registrada com sucesso!', 'success')
    except Exception as e:
        conn.rollback()
        flash(f'Erro ao registrar devolução: {e}', 'danger')
    finally:
        conn.close()
    return redirect(url_for('emprestimos'))

@app.route('/emprestimos/excluir/<int:id_emprestimo>', methods=['POST'])
@login_required
@admin_required
def excluir_emprestimo(id_emprestimo):
    conn = conectar()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute("SELECT status FROM Emprestimo WHERE ID_emprestimo = %s", (id_emprestimo,))
        emprestimo_status = cursor.fetchone()

        if emprestimo_status and emprestimo_status['status'] == 'Ativo':
            flash('Não é possível excluir um empréstimo ativo. Por favor, realize a devolução primeiro.', 'danger')
            return redirect(url_for('emprestimos'))

        cursor.execute("DELETE FROM Emprestimo WHERE ID_emprestimo = %s", (id_emprestimo,))
        conn.commit()
        flash('Empréstimo excluído com sucesso!', 'success')
    except Exception as e:
        conn.rollback()
        flash(f'Erro ao excluir empréstimo: {e}', 'danger')
    finally:
        conn.close()
    return redirect(url_for('emprestimos'))

# --- CRUD DE RESERVAS ---
@app.route('/reservas')
@login_required
@admin_required
def reservas():
    conn = conectar()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute("""
            SELECT R.*, U.nome as usuario_nome, I.titulo as item_titulo
            FROM Reserva R
            JOIN Usuario U ON R.CPF = U.CPF
            JOIN Item_acervo I ON R.ID_item = I.ID_item
            ORDER BY R.data_reserva DESC
        """)
        lista_reservas = cursor.fetchall()
        return render_template('reservas.html', reservas=lista_reservas)
    except Exception as e:
        flash(f'Erro ao carregar reservas: {e}', 'danger')
        return redirect(url_for('index'))
    finally:
        conn.close()

@app.route('/reservas/nova/<int:id_item>', methods=['POST'])
@login_required
@admin_required
def nova_reserva(id_item):
    conn = conectar()
    cursor = conn.cursor(dictionary=True)
    try:
        cpf_usuario = request.form['cpf_usuario']
        data_reserva = date.today().isoformat()
        
        cursor.execute("INSERT INTO Reserva (data_reserva, status_reserva, CPF, ID_item) VALUES (%s, %s, %s, %s)",
                       (data_reserva, 'Ativa', cpf_usuario, id_item))
        conn.commit()
        flash('Reserva realizada com sucesso!', 'success')
    except Exception as e:
        conn.rollback()
        flash(f'Erro ao criar reserva: {e}', 'danger')
    finally:
        conn.close()
    return redirect(url_for('itens'))

@app.route('/reservas/cancelar/<int:id_reserva>', methods=['POST'])
@login_required
@admin_required
def cancelar_reserva(id_reserva):
    conn = conectar()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute("SELECT ID_item FROM Reserva WHERE ID_reserva = %s", (id_reserva,))
        resultado = cursor.fetchone()
        if not resultado:
            flash('Reserva não encontrada.', 'danger')
            return redirect(url_for('reservas'))
        
        id_item = resultado['ID_item']
        
        cursor.execute("DELETE FROM Reserva WHERE ID_reserva = %s", (id_reserva,))
        
        cursor.execute("SELECT COUNT(*) as total FROM Reserva WHERE ID_item = %s AND status_reserva = 'Ativa'", (id_item,))
        total_reservas_ativas = cursor.fetchone()['total']
        
        if total_reservas_ativas == 0:
            cursor.execute("UPDATE Item_acervo SET status_item = 'Disponível' WHERE ID_item = %s AND status_item = 'Reservado'", (id_item,))

        conn.commit()
        flash('Reserva cancelada com sucesso.', 'success')
    except Exception as e:
        conn.rollback()
        flash(f'Erro ao cancelar reserva: {e}', 'danger')
    finally:
        conn.close()
    return redirect(url_for('reservas'))


# --- ROTA DE MOVIMENTAÇÕES ---
@app.route('/movimentacoes')
@login_required
@admin_required
def movimentacoes():
    conn = conectar()
    cursor = conn.cursor(dictionary=True)
    try:
        query = """
            SELECT 
                M.data_movimentacao, 
                M.tipo, 
                I.titulo AS item_titulo,
                U.nome AS usuario_nome
            FROM Movimentacao M
            JOIN Item_acervo I ON M.ID_item = I.ID_item
            JOIN Emprestimo E ON M.ID_emprestimo = E.ID_emprestimo
            JOIN Usuario U ON E.CPF = U.CPF
            ORDER BY M.data_movimentacao DESC, M.ID_emprestimo DESC
        """
        cursor.execute(query)
        lista_movimentacoes = cursor.fetchall()
        return render_template('movimentacoes.html', movimentacoes=lista_movimentacoes)
    except Exception as e:
        flash(f'Erro ao carregar movimentações: {e}', 'danger')
        return redirect(url_for('index'))
    finally:
        conn.close()

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)