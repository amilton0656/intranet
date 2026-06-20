# Padrões do Projeto Intranet

## Padrão de Navbar para novos apps

Todo novo app deve seguir o padrão do **Cota 365** (`apps/cota365/templates/cota365/base.html`):

### Estrutura
Duas barras de menu empilhadas, sem espaço entre elas:

1. **Navbar principal da intranet** (topo)
   - Incluída via `{% include 'intranet/intranet_navbar.html' %}`
   - CSS carregado via `{% static 'intranet/css/navbar.css' %}`
   - Não alterar cores — manter igual à página inicial

2. **Navbar secundária do app** (abaixo)
   - Fundo: `#A7A3AB`
   - Fonte: `#282828`
   - Hover/active: `background: rgba(0,0,0,.1)`, cor `#282828`
   - Usar um ID único (ex: `id="cota365-navbar"`) para escopar o CSS e não interferir na navbar principal
   - **Não usar `margin-top` negativo** — as duas navbars se encostam naturalmente quando o template inclui `intranet_navbar.html` diretamente. O `margin-top: -24px` do Bliss é uma exceção porque ele estende `intranet_base.html`, que adiciona espaço extra.

### CSS base da navbar secundária
```css
#meuapp-navbar {
  background: #A7A3AB !important;
  padding: 0.6rem 1.5rem;
}
#meuapp-navbar .navbar-brand {
  color: #282828 !important;
}
#meuapp-navbar .nav-link {
  color: rgba(40,40,40,.85) !important;
  font-size: 0.85rem;
  padding: 0.4rem 0.9rem !important;
  border-radius: 6px;
  transition: background .2s;
}
#meuapp-navbar .nav-link:hover,
#meuapp-navbar .nav-link.active {
  background: rgba(0,0,0,.1);
  color: #282828 !important;
}
```

### Template base mínimo
```html
{% load static %}
<!DOCTYPE html>
<html lang="pt-BR">
<head>
  ...
  <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/css/bootstrap.min.css">
  <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap-icons@1.11.3/font/bootstrap-icons.css">
  <link rel="stylesheet" href="{% static 'intranet/css/navbar.css' %}">
  <style>
    /* estilos do app aqui */
  </style>
</head>
<body>

{% include 'intranet/intranet_navbar.html' %}

<nav id="meuapp-navbar" class="navbar navbar-expand-lg">
  ...
</nav>

{% block content %}{% endblock %}

</body>
</html>
```
