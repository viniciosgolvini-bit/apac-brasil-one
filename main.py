from fastapi import FastAPI, HTTPException, UploadFile, File, Form
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from geopy.geocoders import Nominatim
import pandas as pd
import io
import httpx
import uvicorn
import os
import re

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

geolocator = Nominatim(user_agent="apac_fleet_analyst_v1", timeout=30)

def limpar_endereco(texto: str):
    return f"{re.sub(r'[-/]', ' ', str(texto))}, Brasil"

@app.get("/", response_class=HTMLResponse)
async def home():
    with open("index.html", "r", encoding="utf-8") as f:
        return f.read()

# ROTA CORRIGIDA: Processar planilha de frota
@app.post("/processar-planilha")
async def processar_planilha(file: UploadFile = File(...), consumo_padrao: float = Form(...)):
    try:
        content = await file.read()
        
        # Lê Excel ou CSV tratando o separador automaticamente
        if file.filename.endswith('.csv'):
            df = pd.read_csv(io.BytesIO(content), sep=',')
            if len(df.columns) <= 1:
                df = pd.read_csv(io.BytesIO(content), sep=';')
        else:
            df = pd.read_excel(io.BytesIO(content))

        # --- BLINDAGEM DO CABEÇALHO ---
        def limpar_nome_coluna(col):
            col_limpa = str(col).strip().replace("“", "").replace("”", "").replace("'", "").replace("’", "")
            col_limpa = col_limpa.lower().replace("â", "a").replace("ã", "a").replace("á", "a").replace("ç", "c")
            return col_limpa

        mapeamento_colunas = {limpar_nome_coluna(c): c for c in df.columns}
        
        if 'origem' not in mapeamento_colunas or 'destino' not in mapeamento_colunas:
            raise HTTPException(
                status_code=400, 
                detail="A planilha deve ter colunas válidas chamadas 'Origem' e 'Destino'."
            )

        coluna_origem_real = mapeamento_colunas['origem']
        coluna_destino_real = mapeamento_colunas['destino']
        # ------------------------------

        total_viagens = len(df)
        gargalos = []
        prejuizo_acumulado = 0.0
        
        # Analisa as rotas gerando os dados mockados de simulação
        for i, row in df.iterrows():
            origem_texto = row[coluna_origem_real]
            destino_texto = row[coluna_destino_real]
            
            valor_perda = round(30 + (i * 2.5), 2)
            
            # Adiciona na lista visual apenas as 5 primeiras para visualização do BI
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
                "prejuizo_total_frota": f"R$ {prejuizo_acumulado:.2f}", # Chave corrigida esperada pelo HTML
                "alerta_critico": "Trechos Urbanos com +20% de desperdício detectados."
            },
            "gargalos_identificados": gargalos
        }
    except HTTPException as http_e:
        raise http_e
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao ler arquivo no servidor: {str(e)}")

@app.post("/calcular-real")
async def calcular_real(dados: dict):
    pass 

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
