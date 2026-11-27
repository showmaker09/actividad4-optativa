"""Pruebas unitarias con mocks para resiliencia_cloud.py (Actividad 5).

Verifica la construcción de la URI resiliente, los reintentos con Exponential
Backoff ante errores transitorios de red, el aborto inmediato ante errores
lógicos y el retorno del identificador insertado, sin requerir conexión real.
"""

import unittest
from unittest.mock import MagicMock, patch
from urllib.parse import parse_qsl, urlsplit

from pymongo.errors import (
    AutoReconnect,
    DuplicateKeyError,
    NetworkTimeout,
    OperationFailure,
)

import resiliencia_cloud as rc


class TestUriResiliente(unittest.TestCase):
    def test_agrega_parametros_obligatorios_sin_duplicar(self):
        base = "mongodb+srv://cluster.ejemplo.mongodb.net/?appName=Cluster"
        resultado = rc.construir_uri_resiliente(base)
        params = parse_qsl(urlsplit(resultado).query)
        claves = [k for k, _ in params]

        self.assertIn(("appName", "Cluster"), params)
        self.assertIn(("retryWrites", "true"), params)
        self.assertIn(("w", "majority"), params)
        self.assertIn(("readPreference", "secondaryPreferred"), params)
        self.assertEqual(len(claves), len(set(claves)))

    def test_reemplaza_parametros_existentes_sin_duplicar(self):
        base = (
            "mongodb+srv://cluster.ejemplo.mongodb.net/"
            "?retryWrites=false&w=1&readPreference=primary&appName=Test"
        )
        resultado = rc.construir_uri_resiliente(base)
        params = parse_qsl(urlsplit(resultado).query)
        mapa = dict(params)

        self.assertEqual(len(params), len(mapa))
        self.assertEqual(mapa["retryWrites"], "true")
        self.assertEqual(mapa["w"], "majority")
        self.assertEqual(mapa["readPreference"], "secondaryPreferred")
        self.assertEqual(mapa["appName"], "Test")

    def test_uri_resiliente_global_incluye_parametros(self):
        mapa = dict(parse_qsl(urlsplit(rc.URI_RESILIENTE).query))
        self.assertEqual(mapa.get("retryWrites"), "true")
        self.assertEqual(mapa.get("w"), "majority")
        self.assertEqual(mapa.get("readPreference"), "secondaryPreferred")


class TestGuardarPaginaResiliente(unittest.TestCase):
    def _mock_db(self, side_effect=None, inserted_id="PAG-001"):
        coleccion = MagicMock()
        resultado = MagicMock()
        resultado.inserted_id = inserted_id
        if side_effect is not None:
            coleccion.insert_one.side_effect = side_effect
        else:
            coleccion.insert_one.return_value = resultado

        db = MagicMock()
        db.__getitem__.return_value = coleccion
        return db, coleccion

    @patch("resiliencia_cloud.time.sleep")
    def test_exito_primer_intento_devuelve_id(self, mock_sleep):
        db, coleccion = self._mock_db(inserted_id="ID-OK-1")
        doc = {"titulo": "Prueba"}

        res = rc.guardar_pagina_resiliente(db, doc)

        self.assertEqual(res, "ID-OK-1")
        db.__getitem__.assert_called_once_with("paginas_digitalizadas")
        coleccion.insert_one.assert_called_once_with(doc)
        mock_sleep.assert_not_called()

    @patch("resiliencia_cloud.time.sleep")
    def test_reintenta_errores_transitorios_y_recupera(self, mock_sleep):
        resultado_ok = MagicMock()
        resultado_ok.inserted_id = "ID-RECUPERADO"
        db, coleccion = self._mock_db(
            side_effect=[
                AutoReconnect("Primario en elección"),
                NetworkTimeout("Tiempo de espera agotado"),
                resultado_ok,
            ]
        )

        res = rc.guardar_pagina_resiliente(db, {"pagina": 1}, max_intentos=3)

        self.assertEqual(res, "ID-RECUPERADO")
        self.assertEqual(coleccion.insert_one.call_count, 3)
        self.assertEqual(
            [llamada.args[0] for llamada in mock_sleep.call_args_list],
            [1, 2],
        )

    @patch("resiliencia_cloud.time.sleep")
    def test_agota_intentos_lanza_runtime_error_con_backoff_1_2_4(self, mock_sleep):
        db, coleccion = self._mock_db(
            side_effect=[
                AutoReconnect("Fallo 1"),
                NetworkTimeout("Fallo 2"),
                AutoReconnect("Fallo 3"),
            ]
        )

        with self.assertRaises(RuntimeError):
            rc.guardar_pagina_resiliente(db, {"pagina": 2}, max_intentos=3)

        self.assertEqual(coleccion.insert_one.call_count, 3)
        self.assertEqual(
            [llamada.args[0] for llamada in mock_sleep.call_args_list],
            [1, 2, 4],
        )

    @patch("resiliencia_cloud.time.sleep")
    def test_aborta_inmediatamente_en_duplicate_key(self, mock_sleep):
        db, coleccion = self._mock_db(
            side_effect=DuplicateKeyError("E11000 duplicate key error")
        )

        with self.assertRaises(DuplicateKeyError):
            rc.guardar_pagina_resiliente(db, {"_id": "DUP-1"}, max_intentos=3)

        self.assertEqual(coleccion.insert_one.call_count, 1)
        mock_sleep.assert_not_called()

    @patch("resiliencia_cloud.time.sleep")
    def test_aborta_inmediatamente_en_operation_failure(self, mock_sleep):
        db, coleccion = self._mock_db(
            side_effect=OperationFailure("Error de validación o cuota")
        )

        with self.assertRaises(OperationFailure):
            rc.guardar_pagina_resiliente(db, {"pagina": 3}, max_intentos=3)

        self.assertEqual(coleccion.insert_one.call_count, 1)
        mock_sleep.assert_not_called()

    @patch("resiliencia_cloud.time.sleep")
    def test_no_reintenta_excepciones_genericas(self, mock_sleep):
        db, coleccion = self._mock_db(side_effect=ValueError("Error inesperado"))

        with self.assertRaises(ValueError):
            rc.guardar_pagina_resiliente(db, {"pagina": 4}, max_intentos=3)

        self.assertEqual(coleccion.insert_one.call_count, 1)
        mock_sleep.assert_not_called()


if __name__ == "__main__":
    unittest.main()
