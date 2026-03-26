"""Exemplo básico de Python para iniciantes.

Inclui:
- leitura de input
- conversão de tipos
- estruturas condicionais if/elif/else
- loops for e while
- listas e funções
- tratamento de erro básico
"""

def verificar_numero():
    # input() lê uma string digitada pelo usuário
    texto = input("Digite um número inteiro: ")

    # Converter string para inteiro com int(); pode lançar ValueError
    try:
        numero = int(texto)
    except ValueError:
        # Captura erros de conversão e avisa o usuário
        print("Valor inválido. Digite um número inteiro.")
        return

    # Estrutura condicional if/elif/else
    if numero > 0:
        print("O número é positivo.")
    elif numero < 0:
        print("O número é negativo.")
    else:
        print("O número é zero.")

    # Expressão condicional (ternária)
    print("Positivo" if numero > 0 else "Negativo ou Zero")


def listar_numeros(n):
    # Função que imprime uma sequência de números de 1 até n
    print(f"Lista de números de 1 até {n}:")
    for i in range(1, n + 1):
        # range(start, stop) não inclui stop, então usamos n+1
        print(i, end=" ")
    print()


def main():
    # Ponto de entrada do script:
    # Tudo aqui será executado quando rodar python exemplo_inicio.py
    print("=== Programa de Introdução ao Python ===")

    # Exemplo de função com entrada do usuário
    verificar_numero()

    # Exemplo de loop while
    limite = 5
    print(f"\nVamos imprimir os primeiros {limite} números usando while:")
    i = 1
    while i <= limite:
        print(i, end=" ")
        i += 1
    print()

    # Exemplo de lista e loop for
    lista = ["Python", "é", "legal"]
    print("\nExemplo de lista:")
    for item in lista:
        print(item, end=" ")
    print()


if __name__ == "__main__":
    main()
