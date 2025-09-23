def cubs_hoje(request):
    hoje = date.today()
    data = date(hoje.year, hoje.month,1)

    indices1 = fetch_indices_data(1, data)
    indices2 = fetch_indices_data(2, data)
    indices3 = fetch_indices_data(1, data)
    indices4 = fetch_indices_data(2, data)
    return render(request, 'indices/postgres.html', {'valor1': indices1[0]['valor'], 'valor2': indices2[0]['valor'], 'valor3': indices3[0]['valor'], 'valor4': indices4[0]['valor']})