# Importando as funções da biblioteca retangulo
import xyz_2 as retangulo

# Função principal do programa
def main():
    # Solicitando os lados do retângulo
    lado1 = float(input("Digite o comprimento do primeiro lado do retângulo: "))
    lado2 = float(input("Digite o comprimento do segundo lado do retângulo: "))

    # Calculando o perímetro e a área usando as funções da biblioteca retangulo
    perimetro = retangulo.calcular_perimetro(lado1, lado2)
    area = retangulo.calcular_area(lado1, lado2)

    # Exibindo os resultados
    print(f"O perímetro do retângulo é: {perimetro}")
    print(f"A área do retângulo é: {area}")


# Chamando a função principal
if __name__ == "__main__":
    main()
