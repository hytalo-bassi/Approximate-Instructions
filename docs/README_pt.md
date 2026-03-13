# Implementação de Instruções Aproximadas em RISC-V

**Autora:** Daniela Luiza Catelan  
**Afiliação:** Professora na Universidade Federal de Mato Grosso do Sul (UFMS)

---

English version available [here](./docs/README.md)

Este repositório demonstra como integrar instruções aproximadas ao conjunto de instruções RISC-V e ao simulador GEM5.

O projeto de instruções aproximadas inclui operações tanto inteiras (addx, subx, mulx, divx) quanto de ponto flutuante (faddx, fsubx, fmulx, fdivx), que fazem parte da minha tese de doutorado sobre "Exploração do Espaço de Design com Computação Aproximada."

## Visão Geral

Este repositório fornece um guia completo para o desenvolvimento e implementação de instruções aproximadas para operações inteiras e de ponto flutuante na arquitetura RISC-V e no simulador GEM5.

## Requisitos

O guia a seguir deve ser consultado para baixar, configurar e utilizar todas as ferramentas: [INSTALLING.md](./docs/INSTALLING.md)

## Desenvolvimento

Contribuições são bem-vindas! Consulte nosso [guia de desenvolvimento](./docs/DEVELOPMENT.md) antes de abrir seu PR!

## Como utilizar

Após instalar todas as ferramentas, você pode começar a utilizá-las da seguinte forma:

```bash
# Compile o arquivo desejado
riscv64-unknown-linux-musl-gcc -O0 -static 
    -march=rv64imafdc 
    -pthread file.c                                     # Substitua file.c pelo seu arquivo C

# Simule
build/RISCV/gem5.opt configs/deprecated/example/se.py
    -c a.out
    # Altere apenas o --num-cpus >= 1. Mantenha todos os
    # outros parâmetros iguais, pois são interdependentes
    --num-cpus=3 --cpu-type=O3CPU --caches --l1d_size=32kB 
    --l1d_assoc=2 --l1i_size=32kB --l1i_assoc=2 --l2_size=256kB 
    --l2_assoc=2 --cpu-clock=1GHz
```

### Saída

Após executar uma simulação, o gem5 gera automaticamente diversos arquivos de estatísticas no diretório `m5out/`. Os arquivos mais relevantes são:

- **config.ini**: Contém informações sobre o tipo de CPU, ISA, cache disponível, largura de bits e mais. Útil para verificar se a configuração da simulação corresponde ao esperado.
- **stats.txt**: O arquivo principal de estatísticas, incluindo tempo de simulação, número de ticks, ciclos de CPU, IPC (Instruções Por Ciclo), informações de cache L1 e mais.

#### Entendendo as Métricas

No arquivo `stats.txt`, você encontrará diversas métricas. Embora nem todas sejam necessárias para cada caso de uso, métricas como tempo de simulação e uso de cache são geralmente úteis.

As métricas seguem o seguinte formato:

```
<nome da métrica>       <valor da métrica>
```

**Exemplo:**
```
simSeconds                      0.000076
simInsts                        111732
...
```

**Métricas mais úteis:**

- `system.cpu.numCycles`: Número total de ciclos de CPU
- `simSeconds`: Tempo total de simulação em segundos
- `simInsts`: Número total de instruções simuladas
- `system.cpu.ipc`: Instruções por ciclo (IPC)

**Outras métricas potencialmente úteis:**

- `system.cpu.commitStats0.numFpInsts`: Número de instruções de ponto flutuante
- `system.cpu.commitStats0.numIntInsts`: Número de instruções inteiras
- `system.cpu.commitStats0.numLoadInsts`: Número de instruções de leitura (load)
- `system.cpu.commitStats0.numStoreInsts`: Número de instruções de escrita (store)
- `system.cpu.commitStats0.numVecInsts`: Número de instruções vetoriais

#### Estatísticas de Energia

Por padrão, o gem5 não coleta estatísticas de consumo de energia.

## Referências

### Levantamentos Bibliográficos

- Vasileios Leon, Muhammad Abdullah Hanif, Giorgos Armeniakos, Xun Jiao, Muhammad Shafique, Kiamal Pekmestzi, Dimitrios Soudris (2025). [*Approximate Computing Survey, Part I: Terminology and Software & Hardware Approximation Techniques*](https://dl.acm.org/doi/10.1145/3716845).
- Vasileios Leon, Muhammad Abdullah Hanif, Giorgos Armeniakos, Xun Jiao, Muhammad Shafique, Kiamal Pekmestzi, Dimitrios Soudris (2025). [*Approximate Computing Survey, Part II: Application-Specific & Architectural Approximation Techniques and Applications*](https://dl.acm.org/doi/10.1145/3711683).

### Outros

- Daniela Catelan, Ricardo Santos, Liana Duenha (2022). [*Evaluation and characterization of approximate arithmetic circuits*](https://onlinelibrary.wiley.com/doi/10.1002/cpe.6865).
- Daniela Catelan, Felipe Sovernigo, Liana Duenha, Ricardo Santos (2024). [*An Instruction-Set Extension to Support Approximate Multicore Processors*](https://ieeexplore.ieee.org/document/10764671).

## Contato

**Daniela Luiza Catelan**  
E-mail: daniela.catelan@ufms.br  
Universidade Federal de Mato Grosso do Sul (UFMS)