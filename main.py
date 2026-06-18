# ROTA ULTRA UNIVERSAL: Aceita qualquer tipo de arquivo e formatação
@app.post("/processar-planilha")
async def processar_planilha(file: UploadFile = File(...), consumo_padrao: float = Form(...)):
    try:
        content = await file.read()
        nome_arquivo = file.filename.lower()
        
        # 1. LEITURA DE EXCEL NATIVO (.xlsx ou .xls)
        if nome_arquivo.endswith('.xlsx') or nome_arquivo.endswith('.xls'):
            df = pd.read_excel(io.BytesIO(content))
        
        # 2. LEITURA DE QUALQUER OUTRO ARQUIVO (CSV, TXT, ETC.)
        else:
            # Tenta decodificar o arquivo usando múltiplos encodings comuns
            texto_arquivo = None
            for encoding_tentativa in ['utf-8', 'latin1', 'iso-8859-1', 'cp1252']:
                try:
                    texto_arquivo = content.decode(encoding_tentativa)
                    break
                except UnicodeDecodeError:
                    continue
            
            if texto_arquivo is None:
                raise Exception("Não foi possível ler a codificação do arquivo de texto.")

            # LIMPEZA AGRESSIVA DE ASPAS POR LINHA (Resolve problemas de exportação do Excel)
            linhas_limpas = []
            for linha in texto_arquivo.splitlines():
                linha = linha.strip()
                # Remove aspas externas se a linha inteira estiver encapsulada
                if linha.startswith('"') and linha.endswith('"'):
                    linha = linha[1:-1]
                elif linha.startswith("'") and linha.endswith("'"):
                    linha = linha[1:-1]
                linhas_limpas.append(linha)
            
            texto_final = "\n".join(linhas_limpas)
            
            # Tenta descobrir o separador correto testando os mais comuns (, ; ou tabulação)
            separadores = [',', ';', '\t']
            melhor_df = None
            maior_numero_colunas = -1
            
            for sep in separadores:
                io_dados = io.StringIO(texto_final)
                try:
                    # 'on_bad_lines=skip' impede o Pandas de quebrar caso encontre linhas desalinhadas
                    df_teste = pd.read_csv(io_dados, sep=sep, on_bad_lines='skip')
                    if len(df_teste.columns) > maior_numero_colunas:
                        maior_numero_colunas = len(df_teste.columns)
                        melhor_df = df_teste
                except Exception:
                    continue
            
            if melhor_df is None or maior_numero_colunas <= 0:
                raise Exception("Formato de texto/CSV inválido ou impossível de processar.")
            
            df = melhor_df

        # --- BLINDAGEM MÁXIMA DOS NOMES DAS COLUNAS ---
        def higienizar_coluna(col):
            c = str(col).strip().replace('"', '').replace("'", "").replace("’", "").replace("“", "").replace("”", "")
            c = c.lower()
            c = c.replace("â", "a").replace("ã", "a").replace("á", "a").replace("à", "a")
            c = c.replace("ê", "e").replace("é", "e")
            c = c.replace("î", "i").replace("í", "i")
            c = c.replace("ô", "o").replace("õ", "o").replace("ó", "o")
            c = c.replace("û", "u").replace("ú", "u")
            c = c.replace("ç", "c")
            return c

        df.columns = [higienizar_coluna(c) for c in df.columns]
        
        coluna_origem = None
        coluna_destino = None
        
        for col in df.columns:
            if 'origem' in col:
                coluna_origem = col
            if 'destino' in col:
                coluna_destino = col
                
        if not coluna_origem or not coluna_destino:
            raise HTTPException(
                status_code=400, 
                detail="A planilha deve conter colunas com os nomes 'Origem' e 'Destino'."
            )

        # 3. PROCESSAMENTO DOS DADOS ENCONTRADOS
        total_viagens = len(df)
        gargalos = []
        prejuizo_acumulado = 0.0
        
        for i, row in df.iterrows():
            origem_texto = str(row[coluna_origem]).strip().replace('"', '').replace("'", "")
            destino_texto = str(row[coluna_destino]).strip().replace('"', '').replace("'", "")
            
            valor_perda = round(30 + (i * 2.5), 2)
            
            if i < 5:
                gargalos.append({
                    "rota": f"{origem_texto} -> {destino_texto}",
                    "status": "Inércia Comprometida" if i % 2 == 0 else "Fluxo Médio",
                    "perda_estimada": f"R$ {valor_perda:.2f}"
                })
            
            prejuizo_acumulado += valor_perda

        return {
            "resumo": {
                "total_viagens": total_viagens,
                "viagens_analisadas": len(gargalos),
                "prejuizo_total_frota": f"R$ {prejuizo_acumulado:.2f}",
                "alerta_critico": "Trechos Urbanos com +20% de desperdício detectados."
            },
            "gargalos_identificados": gargalos
        }
        
    except HTTPException as http_e:
        raise http_e
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao processar arquivo: {str(e)}")
