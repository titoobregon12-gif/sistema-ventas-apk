"""
Sistema Ventas PRO - VERSION KIVY para APK Android
Esta SI se puede convertir a APK con buildozer / build.yml
Mantiene: barcode, stock automatico, tickets, historial, cierre de caja
"""
from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.textinput import TextInput
from kivy.uix.scrollview import ScrollView
from kivy.uix.popup import Popup
from kivy.metrics import dp
import json
from datetime import datetime, date
from decimal import Decimal
from pathlib import Path

DATA_FILE = Path("datos.json")
TICKETS_DIR = Path("tickets")
TICKETS_DIR.mkdir(exist_ok=True)

def to_decimal(v):
    try: return Decimal(str(v)).quantize(Decimal("0.01"))
    except: return Decimal("0")

class Producto:
    def __init__(self, id, nombre, costo, precio_venta, stock, barcode=""):
        self.id=id.strip().upper()
        self.nombre=nombre.strip()
        self.costo=to_decimal(costo)
        self.precio_venta=to_decimal(precio_venta)
        self.stock=int(stock)
        self.barcode=str(barcode).strip()
    def to_dict(self): return {"id":self.id,"nombre":self.nombre,"costo":str(self.costo),"precio_venta":str(self.precio_venta),"stock":self.stock,"barcode":self.barcode}
    @classmethod
    def from_dict(cls,d): return cls(d["id"],d["nombre"],d["costo"],d["precio_venta"],d["stock"],d.get("barcode",""))
    @property
    def margen(self):
        if self.precio_venta==0: return Decimal("0")
        return ((self.precio_venta-self.costo)/self.precio_venta*100).quantize(Decimal("0.1"))

class Sistema:
    def __init__(self):
        self.productos={}
        self.ventas=[]
        self.carrito={}
        self.cargar()
    def cargar(self):
        if not DATA_FILE.exists(): return
        try:
            data=json.loads(DATA_FILE.read_text(encoding="utf-8"))
            self.productos={pid:Producto.from_dict(pd) for pid,pd in data.get("productos",{}).items()}
            self.ventas=data.get("ventas",[])
        except: pass
    def guardar(self):
        data={"productos":{k:v.to_dict() for k,v in self.productos.items()},"ventas":self.ventas}
        DATA_FILE.write_text(json.dumps(data,indent=2,ensure_ascii=False),encoding="utf-8")
    def buscar_barcode(self, code):
        code=code.strip().upper()
        for p in self.productos.values():
            if p.id==code or p.barcode==code or p.barcode.upper()==code: return p
        return None
    def vender(self):
        if not self.carrito: raise Exception("Carrito vacio")
        # validar stock
        for pid,cant in self.carrito.items():
            if self.productos[pid].stock < cant: raise Exception("%s solo %s stock" % (self.productos[pid].nombre, self.productos[pid].stock))
        total=0
        detalle=[]
        for pid,cant in self.carrito.items():
            p=self.productos[pid]
            p.stock-=cant
            sub=float(p.precio_venta*cant)
            total+=sub
            detalle.append("%s x%s" % (p.nombre,cant))
        venta={"id":len(self.ventas)+1,"fecha":datetime.now().isoformat(),"items":detalle,"total":total}
        self.ventas.append(venta)
        self.guardar()
        self.carrito={}
        # ticket SUNAT
        ticket_path=TICKETS_DIR / ("ticket_%04d_%s.txt" % (venta["id"], datetime.now().strftime("%Y%m%d_%H%M%S")))
        ticket_path.write_text("TICKET %04d\nFecha %s\n%s\nTOTAL S/ %.2f\n" % (venta["id"],venta["fecha"],"\n".join(detalle),total),encoding="utf-8")
        return venta

class POSApp(App):
    def build(self):
        self.sistema=Sistema()
        if not self.sistema.productos:
            for p in [Producto("P001","Laptop HP",1800,2500,10,"750001"),Producto("P002","Mouse",35,70,50,"750002"),Producto("P003","Teclado",90,160,30,""),Producto("P004","Cargador",7,15,20,"")]:
                self.sistema.productos[p.id]=p
            self.sistema.guardar()

        root=BoxLayout(orientation="vertical",padding=dp(10),spacing=dp(10))
        # Lector
        lector=BoxLayout(size_hint_y=None,height=dp(50),spacing=dp(5))
        lector.add_widget(Label(text="BARCODE:",size_hint_x=None,width=dp(70)))
        self.input_barcode=TextInput(multiline=False,hint_text="Escanea aqui + Enter",font_size=dp(16))
        self.input_barcode.bind(on_text_validate=self.on_scan)
        lector.add_widget(self.input_barcode)
        lector.add_widget(Button(text="Agregar",on_press=self.on_scan,size_hint_x=None,width=dp(80)))
        root.add_widget(lector)
        
        self.lbl_status=Label(text="Listo para escanear - Stock baja auto",size_hint_y=None,height=dp(25),color=(0,0.6,0,1))
        root.add_widget(self.lbl_status)

        # Inventario
        root.add_widget(Label(text="Inventario (toca para agregar al carrito)",size_hint_y=None,height=dp(25),bold=True))
        self.box_productos=GridLayout(cols=1,size_hint_y=None,spacing=dp(2))
        self.box_productos.bind(minimum_height=self.box_productos.setter('height'))
        scroll_prod=ScrollView(size_hint=(1,0.4))
        scroll_prod.add_widget(self.box_productos)
        root.add_widget(scroll_prod)

        # Carrito
        root.add_widget(Label(text="Carrito",size_hint_y=None,height=dp(25),bold=True))
        self.box_carrito=GridLayout(cols=1,size_hint_y=None,spacing=dp(2))
        self.box_carrito.bind(minimum_height=self.box_carrito.setter('height'))
        scroll_cart=ScrollView(size_hint=(1,0.3))
        scroll_cart.add_widget(self.box_carrito)
        root.add_widget(scroll_cart)

        self.lbl_total=Label(text="Total: S/ 0.00",size_hint_y=None,height=dp(35),font_size=dp(18),bold=True)
        root.add_widget(self.lbl_total)

        # BOTONES QUE PEDISTE
        btns=GridLayout(cols=2,size_hint_y=None,height=dp(180),spacing=dp(5))
        btns.add_widget(Button(text="COBRAR\n+ BAJAR STOCK",background_color=(0.15,0.39,0.92,1),on_press=self.cobrar))
        btns.add_widget(Button(text="REIMPRIMIR\nULTIMO TICKET",background_color=(0.08,0.64,0.29,1),on_press=self.reimprimir))
        btns.add_widget(Button(text="VER HISTORIAL\nCOMPLETO",background_color=(0.2,0.24,0.33,1),on_press=self.ver_historial))
        btns.add_widget(Button(text="REPORTE DIA\nCIERRE CAJA",background_color=(0.91,0.34,0.04,1),on_press=self.cierre_caja))
        root.add_widget(btns)

        self.refresh()
        return root

    def on_scan(self, *args):
        code=self.input_barcode.text.strip()
        if not code: return
        p=self.sistema.buscar_barcode(code)
        if p:
            if p.stock <= self.sistema.carrito.get(p.id,0):
                self.lbl_status.text="❌ Sin stock %s" % p.nombre
            else:
                self.sistema.carrito[p.id]=self.sistema.carrito.get(p.id,0)+1
                self.lbl_status.text="✅ %s x%s" % (p.nombre,self.sistema.carrito[p.id])
                self.refresh_carrito()
        else:
            self.lbl_status.text="⚠️ No existe: %s - Crealo en + Nuevo" % code
        self.input_barcode.text=""

    def refresh(self):
        self.box_productos.clear_widgets()
        for p in self.sistema.productos.values():
            btn=Button(text="%s | %s | S/%.2f | Stock:%s | BC:%s" % (p.id,p.nombre,float(p.precio_venta),p.stock,p.barcode or "-"),size_hint_y=None,height=dp(45),halign="left")
            btn.bind(on_press=lambda x, pid=p.id: self.add_to_cart(pid))
            self.box_productos.add_widget(btn)
        self.refresh_carrito()
        self.lbl_total.text="Total: S/ %.2f | Hoy: %s ventas" % (sum(float(self.sistema.productos[pid].precio_venta*cant) for pid,cant in self.sistema.carrito.items()), len([v for v in self.sistema.ventas if v["fecha"][:10]==date.today().isoformat()]))

    def refresh_carrito(self):
        self.box_carrito.clear_widgets()
        total=0
        for pid,cant in self.sistema.carrito.items():
            p=self.sistema.productos[pid]
            sub=float(p.precio_venta*cant)
            total+=sub
            row=BoxLayout(size_hint_y=None,height=dp(40),spacing=dp(5))
            row.add_widget(Label(text="%s x%s = S/%.2f" % (p.nombre,cant,sub)))
            row.add_widget(Button(text="X",size_hint_x=None,width=dp(40),background_color=(0.8,0.2,0.2,1),on_press=lambda x, pid=pid: self.remove_cart(pid)))
            self.box_carrito.add_widget(row)
        self.lbl_total.text="Total: S/ %.2f" % total

    def add_to_cart(self, pid):
        self.sistema.carrito[pid]=self.sistema.carrito.get(pid,0)+1
        self.refresh_carrito()

    def remove_cart(self, pid):
        self.sistema.carrito.pop(pid,None)
        self.refresh_carrito()

    def cobrar(self, *args):
        try:
            venta=self.sistema.vender()
            Popup(title="Venta OK",content=Label(text="Venta #%04d\nTotal S/ %.2f\nStock bajado auto\nTicket en tickets/" % (venta["id"],venta["total"])),size_hint=(0.8,0.5)).open()
            self.refresh()
        except Exception as e:
            Popup(title="Error",content=Label(text=str(e)),size_hint=(0.8,0.4)).open()

    def reimprimir(self, *args):
        if not self.sistema.ventas:
            Popup(title="Aviso",content=Label(text="No hay ventas"),size_hint=(0.7,0.4)).open()
            return
        v=self.sistema.ventas[-1]
        Popup(title="Ticket",content=Label(text="Ultimo: #%04d S/ %.2f\n%s\nGuardado en tickets/" % (v["id"],v["total"],"\n".join(v["items"]))),size_hint=(0.9,0.6)).open()

    def ver_historial(self, *args):
        box=BoxLayout(orientation="vertical")
        scroll=ScrollView()
        grid=GridLayout(cols=1,size_hint_y=None,spacing=dp(2))
        grid.bind(minimum_height=grid.setter('height'))
        for v in reversed(self.sistema.ventas[-50:]):
            grid.add_widget(Label(text="#%04d %s S/%.2f - %s" % (v["id"],v["fecha"][11:16],v["total"],", ".join(v["items"])[:40]),size_hint_y=None,height=dp(30)))
        scroll.add_widget(grid)
        box.add_widget(scroll)
        box.add_widget(Button(text="Cerrar",size_hint_y=None,height=dp(50),on_press=lambda x: popup.dismiss()))
        popup=Popup(title="Historial Completo - Doble para reimprimir",content=box,size_hint=(0.95,0.9))
        popup.open()

    def cierre_caja(self, *args):
        hoy=date.today().isoformat()
        ventas_hoy=[v for v in self.sistema.ventas if v["fecha"][:10]==hoy]
        total=sum(v["total"] for v in ventas_hoy)
        box=BoxLayout(orientation="vertical",padding=dp(10),spacing=dp(10))
        box.add_widget(Label(text="CIERRE DE CAJA\n%s" % hoy,font_size=dp(18),bold=True,size_hint_y=None,height=dp(60)))
        box.add_widget(Label(text="Ventas hoy: %s\nTotal: S/ %.2f\nTickets: %s archivos" % (len(ventas_hoy),total,len(list(TICKETS_DIR.glob("*")))),font_size=dp(16)))
        box.add_widget(Button(text="GUARDAR REPORTE EN tickets/",size_hint_y=None,height=dp(50),on_press=lambda x: self.guardar_cierre(ventas_hoy,total)))
        box.add_widget(Button(text="Cerrar",size_hint_y=None,height=dp(50),on_press=lambda x: popup.dismiss()))
        popup=Popup(title="Reporte del Dia",content=box,size_hint=(0.85,0.7))
        popup.open()

    def guardar_cierre(self, ventas_hoy, total):
        path=TICKETS_DIR / ("CIERRE_%s.txt" % date.today().strftime("%Y%m%d"))
        path.write_text("CIERRE %s\nVentas %s Total S/ %.2f\n%s\n" % (date.today(),len(ventas_hoy),total,"\n".join(["#%s S/%.2f %s" % (v["id"],v["total"],",".join(v["items"])) for v in ventas_hoy])),encoding="utf-8")
        Popup(title="Guardado",content=Label(text="Guardado en %s" % path),size_hint=(0.8,0.4)).open()

if __name__=="__main__":
    POSApp().run()
