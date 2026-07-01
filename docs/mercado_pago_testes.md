# Credenciais de Teste - Mercado Pago Sandbox (NavieVibe Connect)

Este documento armazena as credenciais das contas de teste (sandbox) do Mercado Pago geradas para a nova aplicação **NavieVibe Connect** no portal de reservas e no painel financeiro do Naviê Vibe.

## 🔑 Credenciais da Aplicação (Configurar no .env)
*   **Número da Aplicação (Client ID):** `3780361702227175`
*   **Access Token (Client Secret):** `APP_USR-3780361702227175-070112-f0854c11ef933d3a3bc036badf9f6b38-3507431941`
*   **Public Key:** `APP_USR-e180ad48-3fc5-4aaa-9ad5-bdc0628e3b91`

---

## 👤 Conta de Teste: Vendedor (Merchant)
*Esta conta deve ser utilizada para fazer o login no Mercado Pago após clicar em **"Conectar com o Mercado Pago"** no painel financeiro.*

*   **User ID:** `3507431941`
*   **E-mail / Usuário:** `TESTUSER8080380469175208771`
*   **Senha:** `XRYf15Cu0y`
*   **Código de verificação:** `431941`

---

## 🛒 Conta de Teste: Comprador (Buyer)
*Esta conta deve ser utilizada para simular a compra de diárias no checkout de reservas do site das pousadas.*

*   **User ID:** `3507431899`
*   **E-mail / Usuário:** `TESTUSER1841139547284627165`
*   **Senha:** `nautjKG0eZ`
*   **Código de verificação:** `431899`

---

## 💳 Cartões de Teste para o Checkout
Para realizar pagamentos simulados no checkout (Pix, cartão, etc.), consulte o menu **TESTES > Cartões de teste** no Mercado Pago Developers ou utilize os dados padrão de teste abaixo:

| Bandeira | Número do Cartão | Código de Segurança (CVV) | Data de Validade |
| :--- | :--- | :--- | :--- |
| **Visa** | `4012 0021 0002 1234` | `123` | Qualquer data futura (ex: `12/30`) |
| **Mastercard** | `5579 1021 0002 1234` | `123` | Qualquer data futura (ex: `12/30`) |
| **Elo** | `6363 6821 0002 1234` | `123` | Qualquer data futura (ex: `12/30`) |

*Nota: Use qualquer nome de titular fictício (ex: "JOÃO SILVA") e preencha um CPF válido fictício no checkout.*
