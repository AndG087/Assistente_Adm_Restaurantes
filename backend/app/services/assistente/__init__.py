"""Assistente que responde perguntas sobre os dados financeiros do restaurante.

periodo.py   — "este mês", "outubro", "últimos 15 dias"... → datas
intencao.py  — pergunta → plano de consulta (regras fixas; IA só como último recurso)
consultas.py — executa o plano no banco e monta a resposta com os valores calculados
servico.py   — orquestra tudo e decide quando é só conversa
"""
