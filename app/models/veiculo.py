import re
from datetime import date

from sqlalchemy.orm import contains_eager

from ..extensions import db
from .erros import ErroRegraNegocio, ErroValidacao
from .marca import Marca
from .util import PRECO_MAXIMO, agora, converter_decimal, converter_inteiro, texto

COMBUSTIVEIS = {
    "FLEX": "Flex",
    "GASOLINA": "Gasolina",
    "ETANOL": "Etanol",
    "DIESEL": "Diesel",
    "HIBRIDO": "Híbrido",
    "ELETRICO": "Elétrico",
}
CAMBIOS = {"MANUAL": "Manual", "AUTOMATICO": "Automático"}
STATUS_VEICULO = {"DISPONIVEL": "Disponível", "RESERVADO": "Reservado", "VENDIDO": "Vendido"}
ORDENACOES = {
    "recentes": "Mais recentes",
    "menor_preco": "Menor preço",
    "maior_preco": "Maior preço",
    "menor_km": "Menor quilometragem",
}

# Placa antiga (ABC1234) ou Mercosul (ABC1D23)
PLACA_RE = re.compile(r"^[A-Z]{3}[0-9][A-Z0-9][0-9]{2}$")
ANO_MINIMO = 1950
KM_MAXIMA = 2_000_000


def _lista_sql(valores):
    return ",".join(f"'{v}'" for v in valores)


class Veiculo(db.Model):
    """Veículo anunciado pela loja."""

    __tablename__ = "veiculo"
    __table_args__ = (
        db.CheckConstraint("preco > 0", name="ck_veiculo_preco"),
        db.CheckConstraint("quilometragem >= 0", name="ck_veiculo_quilometragem"),
        db.CheckConstraint(
            "ano_modelo >= ano_fabricacao AND ano_modelo <= ano_fabricacao + 1",
            name="ck_veiculo_ano_modelo",
        ),
        db.CheckConstraint(f"combustivel IN ({_lista_sql(COMBUSTIVEIS)})", name="ck_veiculo_combustivel"),
        db.CheckConstraint(f"cambio IN ({_lista_sql(CAMBIOS)})", name="ck_veiculo_cambio"),
        db.CheckConstraint(f"status IN ({_lista_sql(STATUS_VEICULO)})", name="ck_veiculo_status"),
    )

    id = db.Column(db.Integer, primary_key=True)
    marca_id = db.Column(db.Integer, db.ForeignKey("marca.id"), nullable=False, index=True)
    modelo = db.Column(db.String(80), nullable=False)
    versao = db.Column(db.String(80))
    ano_fabricacao = db.Column(db.SmallInteger, nullable=False)
    ano_modelo = db.Column(db.SmallInteger, nullable=False)
    cor = db.Column(db.String(30), nullable=False)
    quilometragem = db.Column(db.Integer, nullable=False)
    combustivel = db.Column(db.String(10), nullable=False)
    cambio = db.Column(db.String(10), nullable=False)
    preco = db.Column(db.Numeric(12, 2), nullable=False)
    placa = db.Column(db.String(7), nullable=False, unique=True)
    descricao = db.Column(db.Text)
    imagem = db.Column(db.String(255))
    status = db.Column(db.String(10), nullable=False, default="DISPONIVEL", index=True)
    criado_em = db.Column(db.DateTime, nullable=False, default=agora)
    atualizado_em = db.Column(db.DateTime, nullable=False, default=agora, onupdate=agora)

    marca = db.relationship("Marca", back_populates="veiculos")
    propostas = db.relationship(
        "Proposta",
        back_populates="veiculo",
        cascade="all, delete-orphan",
        order_by="Proposta.criado_em.desc()",
    )
    venda = db.relationship("Venda", back_populates="veiculo", uselist=False)

    # ---------- propriedades de exibição ----------

    @property
    def titulo(self):
        partes = [self.marca.nome if self.marca else "", self.modelo, self.versao or ""]
        return " ".join(p for p in partes if p)

    @property
    def anos(self):
        return f"{self.ano_fabricacao}/{self.ano_modelo}"

    @property
    def combustivel_rotulo(self):
        return COMBUSTIVEIS.get(self.combustivel, self.combustivel)

    @property
    def cambio_rotulo(self):
        return CAMBIOS.get(self.cambio, self.cambio)

    @property
    def status_rotulo(self):
        return STATUS_VEICULO.get(self.status, self.status)

    @property
    def placa_formatada(self):
        """Hífen só na placa antiga (ABC-1234); a Mercosul não usa separador.

        O comprimento é conferido porque o cadastro pela aplicação garante as 7
        posições, mas um registro carregado direto no banco (importação, carga
        inicial via `database/schema.sql`) pode vir fora do formato — e uma
        placa curta derrubava a listagem inteira do painel com IndexError.
        """
        if self.placa and len(self.placa) == 7 and self.placa[4].isdigit():
            return f"{self.placa[:3]}-{self.placa[3:]}"
        return self.placa or ""

    @property
    def placa_mascarada(self):
        """Na vitrine pública só aparece o final da placa (privacidade)."""
        return f"***-**{self.placa[-2:]}" if self.placa else ""

    @staticmethod
    def normalizar_placa(placa):
        return re.sub(r"[^A-Za-z0-9]", "", texto(placa)).upper()

    def como_formulario(self):
        return {
            "marca_id": self.marca_id,
            "modelo": self.modelo,
            "versao": self.versao or "",
            "ano_fabricacao": self.ano_fabricacao,
            "ano_modelo": self.ano_modelo,
            "cor": self.cor,
            "quilometragem": self.quilometragem,
            "combustivel": self.combustivel,
            "cambio": self.cambio,
            "preco": f"{self.preco:.2f}",
            "placa": self.placa,
            "descricao": self.descricao or "",
        }

    # ---------- regras de negócio ----------

    def preencher(self, dados):
        """Valida os dados do formulário e só altera o objeto se todos forem válidos."""
        if self.status == "VENDIDO":
            raise ErroRegraNegocio("Veículos vendidos não podem ser alterados.")

        erros = {}
        ano_atual = date.today().year

        marca_id = converter_inteiro(dados.get("marca_id"))
        if marca_id is None or db.session.get(Marca, marca_id) is None:
            erros["marca_id"] = "Selecione uma marca válida."

        modelo = texto(dados.get("modelo"))
        if not modelo:
            erros["modelo"] = "Informe o modelo do veículo."
        elif len(modelo) > 80:
            erros["modelo"] = "O modelo deve ter no máximo 80 caracteres."

        versao = texto(dados.get("versao"))
        if len(versao) > 80:
            erros["versao"] = "A versão deve ter no máximo 80 caracteres."

        ano_fabricacao = converter_inteiro(dados.get("ano_fabricacao"))
        if ano_fabricacao is None or not ANO_MINIMO <= ano_fabricacao <= ano_atual + 1:
            erros["ano_fabricacao"] = (
                f"O ano de fabricação deve estar entre {ANO_MINIMO} e {ano_atual + 1}."
            )

        ano_modelo = converter_inteiro(dados.get("ano_modelo"))
        if ano_modelo is None:
            erros["ano_modelo"] = "Informe o ano do modelo."
        elif "ano_fabricacao" not in erros and not ano_fabricacao <= ano_modelo <= ano_fabricacao + 1:
            erros["ano_modelo"] = (
                "O ano do modelo deve ser igual ao ano de fabricação ou o ano seguinte."
            )

        cor = texto(dados.get("cor"))
        if not cor:
            erros["cor"] = "Informe a cor do veículo."
        elif len(cor) > 30:
            erros["cor"] = "A cor deve ter no máximo 30 caracteres."

        quilometragem = converter_inteiro(dados.get("quilometragem"))
        if quilometragem is None or not 0 <= quilometragem <= KM_MAXIMA:
            erros["quilometragem"] = "A quilometragem deve ser um número entre 0 e 2.000.000."

        combustivel = texto(dados.get("combustivel")).upper()
        if combustivel not in COMBUSTIVEIS:
            erros["combustivel"] = "Selecione o tipo de combustível."

        cambio = texto(dados.get("cambio")).upper()
        if cambio not in CAMBIOS:
            erros["cambio"] = "Selecione o tipo de câmbio."

        preco = converter_decimal(dados.get("preco"))
        if preco is None or preco <= 0 or preco > PRECO_MAXIMO:
            erros["preco"] = "Informe um preço maior que zero (ex.: 85000,00)."

        placa = self.normalizar_placa(dados.get("placa"))
        if not PLACA_RE.match(placa):
            erros["placa"] = "Placa inválida. Use o formato ABC1234 ou ABC1D23 (Mercosul)."
        else:
            existente = Veiculo.query.filter_by(placa=placa).first()
            if existente and existente.id != self.id:
                erros["placa"] = f"A placa {placa} já está cadastrada em outro veículo."

        descricao = texto(dados.get("descricao"))
        if len(descricao) > 2000:
            erros["descricao"] = "A descrição deve ter no máximo 2000 caracteres."

        if erros:
            raise ErroValidacao(erros)

        self.marca_id = marca_id
        self.modelo = modelo
        self.versao = versao or None
        self.ano_fabricacao = ano_fabricacao
        self.ano_modelo = ano_modelo
        self.cor = cor
        self.quilometragem = quilometragem
        self.combustivel = combustivel
        self.cambio = cambio
        self.preco = preco
        self.placa = placa
        self.descricao = descricao or None
        if self.status is None:
            self.status = "DISPONIVEL"

    def excluir(self):
        if self.venda is not None or self.status == "VENDIDO":
            raise ErroRegraNegocio(
                "Veículo vendido não pode ser excluído, pois faz parte do histórico de vendas."
            )
        db.session.delete(self)

    # ---------- consultas ----------

    @classmethod
    def validar_faixas(cls, filtros):
        """Confere as faixas do catálogo e devolve os erros por campo.

        O JavaScript já avisa sobre a faixa invertida, mas quem monta a URL à
        mão (ou chega por um link antigo) recebia apenas "0 veículos
        encontrados", sem pista do motivo.
        """
        erros = {}
        preco_min = converter_decimal(filtros.get("preco_min"))
        preco_max = converter_decimal(filtros.get("preco_max"))
        if preco_min is not None and preco_max is not None and preco_min > preco_max:
            erros["preco_max"] = (
                "O preço máximo deve ser maior que o mínimo. "
                "Mostrando os resultados sem o filtro de preço."
            )

        ano_min = converter_inteiro(filtros.get("ano_min"))
        ano_max = converter_inteiro(filtros.get("ano_max"))
        if ano_min and ano_max and ano_min > ano_max:
            erros["ano_max"] = (
                "O ano final deve ser maior que o inicial. "
                "Mostrando os resultados sem o filtro de ano."
            )
        return erros

    @classmethod
    def buscar_catalogo(cls, filtros):
        """Consulta da vitrine pública: nunca exibe veículos vendidos."""
        # A marca aparece em todos os cartões do resultado; o contains_eager
        # aproveita o join que já existe e evita uma consulta por cartão.
        consulta = (
            cls.query.join(Marca)
            .options(contains_eager(cls.marca))
            .filter(cls.status != "VENDIDO")
        )

        termo = texto(filtros.get("q"))
        if termo:
            like = f"%{termo}%"
            consulta = consulta.filter(
                db.or_(cls.modelo.ilike(like), cls.versao.ilike(like), Marca.nome.ilike(like))
            )

        marca_id = converter_inteiro(filtros.get("marca"))
        if marca_id:
            consulta = consulta.filter(cls.marca_id == marca_id)

        preco_min = converter_decimal(filtros.get("preco_min"))
        if preco_min is not None:
            consulta = consulta.filter(cls.preco >= preco_min)

        preco_max = converter_decimal(filtros.get("preco_max"))
        if preco_max is not None:
            consulta = consulta.filter(cls.preco <= preco_max)

        ano_min = converter_inteiro(filtros.get("ano_min"))
        if ano_min:
            consulta = consulta.filter(cls.ano_modelo >= ano_min)

        ano_max = converter_inteiro(filtros.get("ano_max"))
        if ano_max:
            consulta = consulta.filter(cls.ano_modelo <= ano_max)

        combustivel = texto(filtros.get("combustivel")).upper()
        if combustivel in COMBUSTIVEIS:
            consulta = consulta.filter(cls.combustivel == combustivel)

        cambio = texto(filtros.get("cambio")).upper()
        if cambio in CAMBIOS:
            consulta = consulta.filter(cls.cambio == cambio)

        ordem = filtros.get("ordem")
        if ordem == "menor_preco":
            consulta = consulta.order_by(cls.preco.asc())
        elif ordem == "maior_preco":
            consulta = consulta.order_by(cls.preco.desc())
        elif ordem == "menor_km":
            consulta = consulta.order_by(cls.quilometragem.asc())
        else:
            consulta = consulta.order_by(cls.criado_em.desc(), cls.id.desc())
        return consulta

    @classmethod
    def buscar_admin(cls, status=None, termo=None):
        consulta = cls.query.join(Marca).options(contains_eager(cls.marca))
        if status in STATUS_VEICULO:
            consulta = consulta.filter(cls.status == status)
        termo = texto(termo)
        if termo:
            like = f"%{termo}%"
            placa = cls.normalizar_placa(termo)
            condicoes = [cls.modelo.ilike(like), Marca.nome.ilike(like)]
            if placa:
                condicoes.append(cls.placa.ilike(f"%{placa}%"))
            consulta = consulta.filter(db.or_(*condicoes))
        return consulta.order_by(cls.criado_em.desc(), cls.id.desc())
