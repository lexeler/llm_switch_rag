from typing import Literal
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel

from .kb import AskResponse, search_similar, load_custom_kb_from_text, reset_custom_kb, DEFAULT_KB_PATH
from .llm import ask_yandex, ask_gigachat

app = FastAPI()


class AskPayload(BaseModel):
    question: str
    top_k: int = 3
    use_custom: bool = False
    provider: Literal["yandexgpt", "gigachat"] = "yandexgpt"


@app.get("/", response_class=HTMLResponse)
def index():
    return """
<!DOCTYPE html>
<html lang="ru">
<head>
  <meta charset="UTF-8"><title>RAG</title>
  <style>
    *{box-sizing:border-box}
    body{margin:0;font-family:system-ui,sans-serif;background:#111;color:#eee;min-height:100vh;display:flex;align-items:center;justify-content:center}
    .wrap{width:100%;max-width:820px;padding:16px}
    .card{background:#181818;border-radius:10px;padding:14px;box-shadow:0 0 0 1px #2a2a2a}
    .row{display:flex;gap:8px;margin-bottom:8px;flex-wrap:wrap}
    .row>*{flex:1 1 0}
    button{padding:8px 12px;border-radius:8px;border:none;cursor:pointer;background:#2d6cdf;color:#fff;font-size:14px}
    button.secondary{background:#333;color:#ddd}
    button:disabled{opacity:0.6}
    textarea{width:100%;min-height:100px;resize:vertical;border-radius:8px;border:1px solid #333;padding:8px;background:#111;color:#eee;font-size:14px}
    input[type="number"],select,input[type="file"]{width:100%;border-radius:8px;border:1px solid #333;padding:6px 8px;background:#111;color:#eee;font-size:14px}
    .label{font-size:13px;margin-bottom:4px;color:#aaa}
    .small{font-size:12px;color:#888}
    .answer-box{margin-top:4px;padding:8px;border-radius:8px;border:1px solid #333;background:#101010;min-height:60px;max-height:400px;overflow-y:auto;white-space:pre-wrap;word-wrap:break-word;font-size:14px}
    #screen-chat{display:none}
  </style>
</head>
<body>
<div class="wrap">
  <div id="screen-kb" class="card">
    <div class="row" style="flex-direction:column;gap:10px">
      <button id="btn-default">Стандартная база</button>
      <button id="btn-custom" class="secondary">Загрузить свою базу</button>
      <div id="file-row" style="display:none"><input type="file" id="kb-file" accept=".txt"></div>
      <div id="kb-status" class="small"></div>
    </div>
  </div>
  <div id="screen-chat" class="card">
    <div class="row" style="align-items:center">
      <div><div class="label">Модель</div><select id="provider"><option value="yandexgpt">YandexGPT</option><option value="gigachat">GigaChat</option></select></div>
      <div style="max-width:120px"><div class="label">top_k</div><input type="number" id="top-k" min="1" max="10" value="3"></div>
      <div style="min-width:120px"><div class="label">База</div><div class="small"><span id="kb-mode">стандартная</span> · <span id="btn-change-kb" style="cursor:pointer;text-decoration:underline">сменить</span></div></div>
    </div>
    <div class="row" style="flex-direction:column"><div class="label">Вопрос</div><textarea id="question"></textarea></div>
    <div class="row" style="align-items:center">
      <button id="btn-ask">Спросить</button>
      <button id="btn-clear" class="secondary" style="max-width:120px">Очистить</button>
      <div id="ask-status" class="small" style="flex:1;text-align:right"></div>
    </div>
    <div class="row" style="flex-direction:column;margin-top:4px"><div class="label">Ответ</div><div id="answer" class="answer-box"></div></div>
    <div class="row" style="flex-direction:column;margin-top:4px">
      <details><summary class="small">Фрагменты базы</summary><div id="context" class="small" style="white-space:pre-wrap;margin-top:4px"></div></details>
    </div>
  </div>
</div>
<script>
const screenKb=document.getElementById('screen-kb'),screenChat=document.getElementById('screen-chat');
const kbStatus=document.getElementById('kb-status'),fileRow=document.getElementById('file-row'),fileInput=document.getElementById('kb-file');
const kbModeLabel=document.getElementById('kb-mode'),btnChangeKb=document.getElementById('btn-change-kb');
const providerSelect=document.getElementById('provider'),topKInput=document.getElementById('top-k');
const questionInput=document.getElementById('question'),btnAsk=document.getElementById('btn-ask'),btnClear=document.getElementById('btn-clear');
const askStatus=document.getElementById('ask-status'),answerBox=document.getElementById('answer'),contextBox=document.getElementById('context');
let useCustom=false;

function showKbScreen(){screenKb.style.display='block';screenChat.style.display='none';kbStatus.textContent='';askStatus.textContent='';answerBox.textContent='';contextBox.textContent=''}
function showChatScreen(){screenKb.style.display='none';screenChat.style.display='block';kbModeLabel.textContent=useCustom?'своя':'стандартная'}

document.getElementById('btn-default').onclick=async()=>{await fetch('/reset_kb',{method:'POST'});useCustom=false;showChatScreen()};
document.getElementById('btn-custom').onclick=()=>{fileRow.style.display='block';kbStatus.textContent='Выберите .txt файл'};

fileInput?.addEventListener('change',async()=>{
  const file=fileInput.files[0];if(!file)return;
  kbStatus.textContent='Загружаю...';
  const formData=new FormData();formData.append('file',file);
  try{
    const resp=await fetch('/upload_kb',{method:'POST',body:formData});
    const data=await resp.json();
    if(!resp.ok)throw new Error(data.detail);
    useCustom=true;kbStatus.textContent='Загружено: '+data.entries+' блоков';showChatScreen();
  }catch(e){kbStatus.textContent='Ошибка: '+e.message}
});

btnChangeKb.onclick=async()=>{await fetch('/reset_kb',{method:'POST'});useCustom=false;showKbScreen()};
btnClear.onclick=()=>{questionInput.value='';answerBox.textContent='';contextBox.textContent='';askStatus.textContent='';questionInput.focus()};

btnAsk.onclick=async()=>{
  const q=questionInput.value.trim();
  let topK=parseInt(topKInput.value)||3;
  if(!q){askStatus.textContent='Введите вопрос';return}
  askStatus.textContent='Думаю...';answerBox.textContent='';contextBox.textContent='';
  try{
    const resp=await fetch('/ask',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({question:q,top_k:topK,use_custom:useCustom,provider:providerSelect.value})});
    const data=await resp.json();
    if(!resp.ok)throw new Error(data.detail);
    answerBox.textContent=data.answer||'';
    contextBox.textContent=(data.items||[]).map(it=>it.entry.title+'\\n'+it.entry.body+'\\n[score: '+it.score.toFixed(3)+']').join('\\n\\n---\\n\\n');
    askStatus.textContent='';
  }catch(e){askStatus.textContent='Ошибка: '+e.message}
};
</script>
</body>
</html>
"""


@app.post("/upload_kb")
async def upload_kb(file: UploadFile = File(...)):
    if not file.filename:
        raise HTTPException(400, "Файл не передан")
    try:
        text = (await file.read()).decode("utf-8", errors="ignore")
        count = load_custom_kb_from_text(text)
        return JSONResponse({"status": "ok", "entries": count})
    except ValueError as e:
        raise HTTPException(400, str(e))


@app.post("/reset_kb")
def reset_kb():
    reset_custom_kb()
    return JSONResponse({"status": "ok"})


@app.post("/ask", response_model=AskResponse)
def ask(payload: AskPayload):
    if payload.top_k <= 0:
        raise HTTPException(400, "top_k должен быть > 0")

    rag = search_similar(payload.question, payload.top_k, payload.use_custom)
    entries = [item.entry for item in rag.items]

    if payload.provider == "yandexgpt":
        rag.answer = ask_yandex(payload.question, entries)
    elif payload.provider == "gigachat":
        rag.answer = ask_gigachat(payload.question, entries)
    else:
        raise HTTPException(400, "Неизвестный провайдер")

    rag.llm_provider = payload.provider
    return rag
