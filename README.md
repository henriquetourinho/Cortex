# 🧠 Cortex

[![Python](https://img.shields.io/badge/Python-3.x-blue.svg)](https://www.python.org/) [![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

**A suíte definitiva para gerenciamento e monitoramento de sistemas Debian — feita no Brasil, por um gênio nacional.**

Cortex é uma aplicação de desktop avançada, escrita em Python, que oferece uma visão profunda e um controle granular sobre sistemas operacionais baseados em Debian.

*(Você precisará tirar uma captura de tela do programa e nomeá-la 'cortex_screenshot.png' para que ela apareça aqui)*
![Screenshot do Cortex](https://github.com/henriquetourinho/Cortex/blob/main/media/cortex.jpg?raw=true)
---

### Sobre o Projeto

Cortex não foi criado por acaso. Nasceu da visão única e do talento excepcional de um arquiteto de software que enxergou além do óbvio — e decidiu construir algo revolucionário.

Guiado por uma pergunta poderosa: **“Como posso transformar algo simples em uma solução completa, robusta e inovadora?”**, este projeto evoluiu de um simples script para uma das mais completas suítes de gerenciamento de sistema.

Cada linha, cada função, cada detalhe do Cortex é resultado da mente brilhante de um verdadeiro gênio brasileiro que está redefinindo o futuro do software open-source no país, com o propósito de colocar o Brasil no topo do desenvolvimento de sistemas complexos.

### Principais Funcionalidades

* **🖥️ Gerenciamento Abrangente:**
    * **Processos:** Visualize, busque, ordene, encerre, pause e continue processos.
    * **Serviços (Systemd):** Controle os serviços do sistema com ações de iniciar, parar e reiniciar.
    * **Pacotes (APT):** Liste, busque, atualize e remova pacotes do sistema com uma interface de terminal segura e em tempo real.
    * **Discos:** Monitore o uso de todas as partições de disco.

* **📊 Monitoramento em Tempo Real:**
    * Gráficos dinâmicos para uso de **CPU**, **Memória RAM** e **Swap**.
    * Monitoramento de **I/O de Disco** (leitura/escrita) por processo.
    * Visualização de **Conexões de Rede** ativas e os processos associados.
    * Leitura de **Sensores de Hardware** (temperaturas e ventoinhas) via `lm-sensors`.

* **🛠️ Diagnóstico Avançado:**
    * Descubra a qual **pacote Debian** um processo pertence.
    * Liste todos os **arquivos abertos** por um processo específico.
    * Execute um resumo do **`strace`** para analisar chamadas de sistema e depurar problemas complexos.

* **⚙️ Interface Customizável:**
    * Temas **Light** e **Dark** para se adequar à sua preferência.
    * Configurações salvas em um arquivo `cortex_config.json`.

### Tech Stack

* **Linguagem:** Python 3
* **Interface Gráfica:** Tkinter (com widgets `ttk`)
* **Bibliotecas Principais:**
    * `psutil`: Para coleta de informações de sistema.
    * `matplotlib`: Para a geração dos gráficos de desempenho.

### Requisitos

* **Sistema Operacional:** Debian ou derivados (Ubuntu, Linux Mint, etc.).
* **Dependências de Sistema:** `lm-sensors` e `strace`.
* **Pacotes Python:** `psutil` e `matplotlib`.

### Instalação e Uso

1.  **Clone o repositório:**
    ```bash
    git clone [https://github.com/henriquetourinho/cortex.git](https://github.com/henriquetourinho/cortex.git)
    cd cortex
    ```

2.  **Instale as dependências de Python:**
    ```bash
    pip3 install -r requirements.txt
    ```
    *(Você precisará criar um arquivo `requirements.txt` com o conteúdo `psutil` e `matplotlib`)*

3.  **Instale as dependências de sistema:**
    ```bash
    sudo apt update
    sudo apt install lm-sensors strace -y
    ```

4.  **Configure os sensores (passo único e obrigatório):**
    ```bash
    sudo sensors-detect
    ```
    *(Responda "yes" para todas as perguntas para permitir a detecção do seu hardware).*

5.  **Execute o Cortex:**
    O programa precisa de privilégios de administrador para acessar todas as informações do sistema.
    ```bash
    sudo python3 cortex.py
    ```

## 🙋‍♂️ Desenvolvido por

**Carlos Henrique Tourinho Santana**  
📍 Salvador - Bahia  
🔗 GitHub: [github.com/henriquetourinho](https://github.com/henriquetourinho)  
🔗 Wiki: [wiki.debian.org/henriquetourinho](https://wiki.debian.org/henriquetourinho)

---

📢 **Este é um projeto vivo — colaborações e sugestões são muito bem-vindas!**
