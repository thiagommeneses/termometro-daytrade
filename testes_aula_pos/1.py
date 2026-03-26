# Exemplo de script para iniciantes em Python
# lê um número, imprime, e usa uma função de saudação

numero = 123
print("O número é:", numero)

# Exemplo de função simples
def saudacao(nome):
    print(f"Olá, {nome}! Bem-vindo ao Python.")


if __name__ == "__main__":
    # Para aceitar argumento via linha de comando (ex: python 1.py Thiago)
    import sys

    nome_do_usuario = "Convidado"
    if len(sys.argv) > 1:
        nome_do_usuario = sys.argv[1]

    saudacao(nome_do_usuario)

