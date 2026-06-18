# NOVO: Rota para processar planilha de frota
@app.post("/processar-planilha")
async def processar_planilha(file: UploadFile = File(...), consumo_padrao: float = Form(...)):
    try:
        content = await file.read()
        
        # Lê Excel ou CSV tratando o separador automaticamente
        if file.filename.endswith('.csv'):
            # Tenta ler com vírgula, se falhar ou ler apenas 1 coluna, tenta ponto e vírgula
            df = pd.read_csv(io.BytesIO(content), sep=',')
            if len(df.columns) <= 1:
                df = pd.read_csv(io.BytesIO(content), sep=';')
        else:
            df = pd.read_excel(io.BytesIO(content))

        # --- BLINDAGEM DO CABEÇALHO ---
        # Remove espaços em branco, aspas simples, aspas duplas curvas e converte para minúsculo
        def limpar_nome_coluna(col):
            col_limpa = str(col).strip().replace("“", "").replace("”", "").replace("'", "").replace("’", "")
            # Remove acentos básicos para garantir a validação
            col_limpa = col_limpa.lower().replace("â", "a").replace("ã", "a").replace("á", "a").replace("ç", "c")
            return col_limpa

        # Cria um mapeamento das colunas originais para as colunas limpas
        mapeamento_colunas = {limpar_nome_coluna(c): c for c in df.columns}
        
        # Valida se as colunas essenciais existem na versão limpa
        if 'origem' not in mapeamento_colunas or 'destino' not in mapeamento_colunas:
            raise HTTPException(
                status_code=400, 
                detail="A planilha deve ter colunas válidas chamadas 'Origem' e 'Destino'."
            )

        # Recupera o nome exato da coluna como ela está escrita no arquivo original do usuário
        coluna_origem_real = mapeamento_colunas['origem']
        coluna_destino_real = mapeamento_colunas['destino']
        # ------------------------------

        # Simulação de análise de gargalos em massa
        total_viagens = len(df)
        gargalos = []
        
        # Analisa as primeiras 5 rotas para exemplo (usando os nomes reais validados)
        for i, row in df.head(5).iterrows():
            origem_texto = row[coluna_origem_real]
            destino_texto = row[coluna_destino_real]
            
            gargalos.append({
                "rota": f"{origem_texto} -> {destino_texto}",
                "status": "Inércia Comprometida" if i % 2 == 0 else "Fluxo Médio",
                "perda_estimada": "R$ " + str(round(30 + (i * 15), 2))
            })

        return {
            "resumo": {
                "total_viagens": total_viagens,
                "viagens_analisadas": len(gargalos),
                "alerta_critico": "Trechos Urbanos com +20% de desperdício detectados."
            },
            "gargalos_identificados": gargalos
        }
    except HTTPException as http_e:
        raise http_e
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao ler arquivo: {str(e)}")
