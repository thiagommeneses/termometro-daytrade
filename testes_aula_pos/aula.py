def nome_da_funcao(parametros=10):
    """Exemplo de função que imprime status sobre valores de 1 até parametros-1."""
    for a in range(1, parametros):
        if a == 10:
            print(f"{a}: Valor de 10")
        elif a < 10:
            print(f"{a}: Abaixo de 10")
        else:
            print(f"{a}: Acima de 10")


def exemplo_lista_numero():
    num = [1, 2, 3, 4, 5]
    for i in num:
        print(f"original: {i}")
    num.append(7)
    print("Após append(7):")
    for i in num:
        print(i)


def exemplo_lista_mista():
    lista = [10, "Texto", 3.14, True]
    for i in lista:
        print(i)


def exemplo_condicional_if(numero):
    # Verifica se o número é positivo, negativo ou zero
    if numero > 0:
        print("O número é positivo.")
    elif numero < 0:
        print("O número é negativo.")
    else:
        print("O número é zero.")

    # Expressão condicional (ternário)
    print("Positivo" if numero > 0 else "Negativo ou Zero")


def exemplo_condicional_usuario():
    texto = input("Digite um número: ")
    try:
        numero = float(texto)
    except ValueError:
        print("Entrada inválida. Digite um número válido.")
        return

    exemplo_condicional_if(numero)


if __name__ == "__main__":
    # Chamada de exemplo
    nome_da_funcao(100)
    print("\n--- exemplo_lista_numero ---")
    exemplo_lista_numero()
    print("\n--- exemplo_lista_mista ---")
    exemplo_lista_mista()
    print("\n--- exemplo_condicional_usuario ---")
    exemplo_condicional_usuario()
    