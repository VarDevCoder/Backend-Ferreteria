"""Casos de uso de Clientes, Proveedores y su catálogo (CU-07, CU-08, CU-09)."""
from app.domain.entities import Cliente, Proveedor, ProveedorProducto, Usuario
from app.domain.enums import RolUsuario
from app.domain.exceptions import ConflictoDeUnicidad, RecursoNoEncontrado, SolicitudInvalida
from app.domain.repositories import (
    ClienteRepository,
    ProveedorProductoRepository,
    ProveedorRepository,
    UsuarioRepository,
)
from app.infrastructure.security.password_hasher import hash_password


class ClienteService:
    def __init__(self, clientes: ClienteRepository):
        self._clientes = clientes

    def listar(
        self, busqueda: str | None = None, activo: bool | None = None, ciudad: str | None = None
    ) -> list[Cliente]:
        return self._clientes.list(busqueda=busqueda, activo=activo, ciudad=ciudad)

    def ciudades(self) -> list[str]:
        return self._clientes.ciudades()

    def obtener(self, cliente_id: int) -> Cliente:
        cliente = self._clientes.get_by_id(cliente_id)
        if cliente is None:
            raise RecursoNoEncontrado("Cliente", cliente_id)
        return cliente

    def crear(self, **datos) -> Cliente:
        cliente = Cliente(id=None, **self._datos_unicos(datos))
        return self._clientes.add(cliente)

    def actualizar(self, cliente_id: int, **datos) -> Cliente:
        actual = self.obtener(cliente_id)
        for campo, valor in self._datos_unicos(datos, excluir_id=cliente_id).items():
            setattr(actual, campo, valor)
        return self._clientes.update(actual)

    def _datos_unicos(self, datos: dict, excluir_id: int | None = None) -> dict:
        """RUC y email vacíos quedan sin cargar; si vienen, no pueden ser de otro cliente."""
        datos = dict(datos)
        for campo in ("ruc", "email"):
            if campo in datos:
                valor = (datos[campo] or "").strip() or None
                datos[campo] = valor.lower() if valor and campo == "email" else valor
        if datos.get("ruc") and self._clientes.existe_ruc(datos["ruc"], excluir_id):
            raise ConflictoDeUnicidad(f"Ya hay un cliente con el RUC {datos['ruc']}")
        if datos.get("email") and self._clientes.existe_email(datos["email"], excluir_id):
            raise ConflictoDeUnicidad(f"Ya hay un cliente con el email {datos['email']}")
        return datos

    def eliminar(self, cliente_id: int) -> None:
        self.obtener(cliente_id)
        if self._clientes.tiene_pedidos(cliente_id):
            raise SolicitudInvalida(
                "No se puede eliminar el cliente porque tiene pedidos o cuenta corriente. Desactívelo en su lugar."
            )
        self._clientes.delete(cliente_id)

    def toggle_activo(self, cliente_id: int) -> Cliente:
        cliente = self.obtener(cliente_id)
        cliente.activo = not cliente.activo
        return self._clientes.update(cliente)


class ProveedorService:
    def __init__(self, proveedores: ProveedorRepository, usuarios: UsuarioRepository):
        self._proveedores = proveedores
        self._usuarios = usuarios

    def listar(self, solo_activos: bool = False) -> list[Proveedor]:
        return self._proveedores.list(solo_activos=solo_activos)

    def obtener(self, proveedor_id: int) -> Proveedor:
        proveedor = self._proveedores.get_by_id(proveedor_id)
        if proveedor is None:
            raise RecursoNoEncontrado("Proveedor", proveedor_id)
        return proveedor

    def obtener_por_usuario(self, user_id: int) -> Proveedor:
        proveedor = self._proveedores.get_by_user_id(user_id)
        if proveedor is None:
            raise RecursoNoEncontrado("Proveedor de usuario", user_id)
        return proveedor

    def crear(
        self,
        razon_social: str,
        ruc: str,
        email: str,
        password: str,
        telefono: str | None = None,
        direccion: str | None = None,
        ciudad: str | None = None,
        rubros: str | None = None,
        notas: str | None = None,
    ) -> Proveedor:
        """Crea primero el `User` con rol proveedor y luego la ficha comercial,
        tal como especifica CU-08."""
        email = email.strip().lower()
        ruc = ruc.strip()
        if self._usuarios.get_by_email(email) is not None:
            raise ConflictoDeUnicidad("Ya existe una cuenta con ese email")
        if self._proveedores.existe_ruc(ruc):
            raise ConflictoDeUnicidad(f"Ya hay un proveedor con el RUC {ruc}")

        usuario = self._usuarios.add(
            Usuario(id=None, name=razon_social, email=email, password_hash=hash_password(password), rol=RolUsuario.PROVEEDOR)
        )
        proveedor = Proveedor(
            id=None, user_id=usuario.id, razon_social=razon_social, ruc=ruc, telefono=telefono,
            direccion=direccion, ciudad=ciudad, rubros=rubros, notas=notas,
        )
        return self._proveedores.add(proveedor)

    def actualizar(self, proveedor_id: int, **datos) -> Proveedor:
        actual = self.obtener(proveedor_id)
        if "ruc" in datos:
            datos["ruc"] = datos["ruc"].strip()
            if self._proveedores.existe_ruc(datos["ruc"], excluir_id=proveedor_id):
                raise ConflictoDeUnicidad(f"Ya hay un proveedor con el RUC {datos['ruc']}")
        for campo, valor in datos.items():
            setattr(actual, campo, valor)
        return self._proveedores.update(actual)

    def toggle_activo(self, proveedor_id: int) -> Proveedor:
        proveedor = self.obtener(proveedor_id)
        usuario = self._usuarios.get_by_id(proveedor.user_id)
        usuario.activo = not usuario.activo
        self._usuarios.update(usuario)
        proveedor.usuario_activo = usuario.activo
        return proveedor


class ProveedorProductoService:
    def __init__(self, items: ProveedorProductoRepository):
        self._items = items

    def listar(
        self, proveedor_id: int | None = None, producto_id: int | None = None, disponible: bool | None = None
    ) -> list[ProveedorProducto]:
        return self._items.list(proveedor_id=proveedor_id, producto_id=producto_id, disponible=disponible)

    def crear(
        self,
        proveedor_id: int,
        producto_id: int,
        precio: int,
        codigo_proveedor: str | None = None,
        nombre_proveedor: str | None = None,
        tiempo_entrega_dias: int | None = None,
        notas: str | None = None,
    ) -> ProveedorProducto:
        if self._items.existe(proveedor_id, producto_id):
            raise ConflictoDeUnicidad("Ese producto ya está en el catálogo de este proveedor. Editalo en su lugar.")
        item = ProveedorProducto(
            id=None, proveedor_id=proveedor_id, producto_id=producto_id, precio=precio,
            codigo_proveedor=codigo_proveedor, nombre_proveedor=nombre_proveedor,
            tiempo_entrega_dias=tiempo_entrega_dias, notas=notas,
        )
        return self._items.add(item)

    def actualizar(self, item_id: int, **datos) -> ProveedorProducto:
        actual = self._obtener(item_id)
        for campo, valor in datos.items():
            setattr(actual, campo, valor)
        return self._items.update(actual)

    def eliminar(self, item_id: int) -> None:
        self._obtener(item_id)
        self._items.delete(item_id)

    def toggle_disponible(self, item_id: int) -> ProveedorProducto:
        item = self._obtener(item_id)
        item.disponible = not item.disponible
        return self._items.update(item)

    def _obtener(self, item_id: int) -> ProveedorProducto:
        item = self._items.get_by_id(item_id)
        if item is None:
            raise RecursoNoEncontrado("ProveedorProducto", item_id)
        return item
