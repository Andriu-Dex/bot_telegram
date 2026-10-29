import { test, expect, Page } from '@playwright/test'

async function mockWorkspace(page: Page) {
  await page.addInitScript(()=>sessionStorage.setItem('ctt_token','ui-test-token'))
  const course={id:1,title:'GitHub QA',status:'ABIERTO',hours:'32 HORAS',content:'DESCRIPCIÓN\nAprende colaboración. Precio $40.',registration_url:'https://example.org/registro',source_url:'https://example.org/curso1.php',approved:true,pending:{title:'GitHub QA actualizado',hours:'40 HORAS',status:'CERRADO',content:'Nueva edición pendiente de revisión',registration_url:''},synced_at:'2026-10-29T12:00:00Z'}
  const base={channel:'simulator',stage:'interesado',course_id:1,priority:0,handoff:false,owner:'Equipo',notes:'Nota guardada',next_action:'Contactar',profile:{objetivo:'Aprender'},sentiment:'interesado',sentiment_reason:'Consulta',summary:'Consulta de prueba',updated_at:'2026-10-29T12:00:00Z'}
  const leads=[{...base,id:1,name:'QA Uno',external_id:'uno'},{...base,id:2,name:'QA Dos',external_id:'dos'}]
  const status={telegram_configured:true,llm_configured:true,llm_provider:'gemini',llm_model:'gemini-2.5-flash',llm_runtime:{successful_calls:0,failed_calls:1,last_success_at:null,last_failure_at:'2026-10-29T12:00:00Z',last_error_code:404,last_error_type:'ClientError'}}
  const patches:any[]=[]
  const errors:string[]=[]
  page.on('pageerror',e=>errors.push(e.message))
  await page.route('**/api/**',async route=>{
    const request=route.request(),path=new URL(request.url()).pathname
    if(path==='/api/events')return route.fulfill({contentType:'text/event-stream',body:'data: {"revision":1}\n\n'})
    if(path==='/api/status')return route.fulfill({json:status})
    if(path==='/api/courses')return route.fulfill({json:[course]})
    if(path==='/api/leads')return route.fulfill({json:leads})
    const match=path.match(/^\/api\/leads\/(\d+)$/)
    if(match && request.method()==='PATCH') {
      const body=request.postDataJSON();patches.push(body)
      const lead=leads.find(l=>l.id===Number(match[1]))!;Object.assign(lead,body)
      return route.fulfill({json:lead})
    }
    const messages=path.match(/^\/api\/leads\/(\d+)\/messages$/)
    if(messages) {
      const id=Number(messages[1]);if(id===2)await new Promise(r=>setTimeout(r,500))
      return route.fulfill({json:[{id,role:'user',text:`Contenido exclusivo ${id}`,delivery:'saved',created_at:'2026-10-29T12:00:00Z'}]})
    }
    if(path==='/api/simulator/messages') {
      await new Promise(r=>setTimeout(r,500))
      return route.fulfill({json:{lead_id:1,mode:'human',reply:null}})
    }
    return route.fulfill({status:404,json:{detail:'Ruta no simulada'}})
  })
  await page.goto('/')
  await expect(page.getByRole('heading',{name:'Una vista clara. Más oportunidades.'})).toBeVisible()
  return {course,leads,status,patches,errors}
}

test('settings distinguishes configured credentials from an unavailable model',async({page})=>{
  const workspace=await mockWorkspace(page)
  await page.getByRole('button',{name:'Configuración',exact:true}).click()
  await expect(page.getByText('Modelo no disponible (HTTP 404)',{exact:true})).toBeVisible()
  await expect(page.getByText('Usando respaldo',{exact:true})).toBeVisible()
  await expect(page.getByText('Gemini 2.5 / Flash activo',{exact:true})).toHaveCount(0)
  workspace.status.llm_runtime.failed_calls=0
  workspace.status.llm_runtime.last_failure_at=null as any
  workspace.status.llm_runtime.last_error_code=null as any
  await page.reload()
  await page.getByRole('button',{name:'Configuración',exact:true}).click()
  await expect(page.getByText('Sin verificar',{exact:true})).toBeVisible()
  expect(workspace.errors).toEqual([])
})

test('switching chats does not reveal previous messages and handover preserves an unsaved draft',async({page})=>{
  const workspace=await mockWorkspace(page)
  await page.getByRole('button',{name:'Conversaciones',exact:true}).click()
  await page.locator('.conversation-item').filter({hasText:'QA Uno'}).click()
  await expect(page.locator('.message.user')).toContainText('Contenido exclusivo 1')
  await page.getByLabel('Notas internas').fill('Borrador sin guardar')
  await page.getByRole('button',{name:'Tomar control',exact:true}).click()
  await expect(page.getByRole('button',{name:'Reanudar IA',exact:true})).toBeVisible()
  expect(workspace.patches[0].notes).toBe('Nota guardada')
  await expect(page.getByLabel('Notas internas')).toHaveValue('Borrador sin guardar')
  await page.locator('.conversation-item').filter({hasText:'QA Dos'}).click()
  await expect(page.getByText('Contenido exclusivo 1',{exact:true})).toHaveCount(0)
  await expect(page.locator('.message.user')).toContainText('Contenido exclusivo 2')
  expect(workspace.errors).toEqual([])
})

test('published filter and pending preview show the data that will actually be approved',async({page})=>{
  await mockWorkspace(page)
  await page.getByRole('button',{name:'Catálogo de cursos',exact:true}).click()
  await page.getByRole('button',{name:'Publicados (1)',exact:true}).click()
  await expect(page.locator('.course-card')).toHaveCount(1)
  await page.getByRole('button',{name:'Revisar ficha',exact:true}).click()
  const modal=page.getByRole('dialog')
  await expect(modal.getByRole('heading')).toHaveText('GitHub QA actualizado')
  await expect(modal).toContainText('40 HORAS')
  await expect(modal).toContainText('CERRADO')
  await expect(modal).toContainText('No publicado')
  await expect(modal.getByText('Enlace oficial de formulario')).toHaveCount(0)
})

test('simulator blocks resetting an in-flight message and explains human handover',async({page})=>{
  const workspace=await mockWorkspace(page)
  await page.getByRole('button',{name:'Simulador',exact:true}).click()
  await page.getByLabel('Mensaje de prueba').fill('Consulta de prueba')
  await page.getByRole('button',{name:'Enviar consulta',exact:true}).click()
  await expect(page.getByRole('button',{name:'Nueva conversación',exact:true})).toBeDisabled()
  await expect(page.getByText('Mensaje registrado para el asesor.',{exact:false})).toBeVisible()
  expect(workspace.errors).toEqual([])
})

test('all views remain navigable and do not overflow on mobile',async({page})=>{
  const workspace=await mockWorkspace(page)
  for(const width of [390,900,1100]) {
    await page.setViewportSize({width,height:844})
    for(const name of ['Resumen','Conversaciones','Catálogo de cursos','Simulador','Configuración']) {
      await page.getByRole('button',{name,exact:true}).click()
      const overflow=await page.evaluate(()=>document.documentElement.scrollWidth>window.innerWidth)
      expect(overflow,`${name} desborda en ${width}px`).toBe(false)
    }
    await page.getByRole('button',{name:'Conversaciones',exact:true}).click()
    await page.locator('.conversation-item').first().click()
    await expect(page.locator('.message.user')).toBeVisible()
    const box=await page.locator('.chat').boundingBox()
    expect(box!.x+box!.width).toBeLessThanOrEqual(width)
  }
  await page.setViewportSize({width:390,height:844})
  await page.getByRole('button',{name:'Conversaciones',exact:true}).click()
  await page.locator('.conversation-item').first().click()
  await expect(page.locator('.message.user')).toBeVisible()
  expect(await page.evaluate(()=>document.documentElement.scrollWidth>window.innerWidth)).toBe(false)
  await page.screenshot({path:'../tmp/ui-review-mobile.png',fullPage:true})
  expect(workspace.errors).toEqual([])
})
