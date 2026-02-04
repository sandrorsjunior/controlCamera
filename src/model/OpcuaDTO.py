class OpcuaDTO:
    """
    Data Transfer Object (Singleton) para gerenciar o estado das variáveis do PLC.
    Atua como fonte única de verdade para a interface gráfica.
    """
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(OpcuaDTO, cls).__new__(cls)
            cls._instance._variables = {}
            cls._instance._observers = []
        return cls._instance

    def set_variable(self, node_id, value):
        """Atualiza o valor e notifica observadores."""
        # Normaliza o valor para evitar lidar com objetos complexos na UI
        final_val = value
        if hasattr(value, 'Value'):
             final_val = value.Value.Value
        
        # Atualiza o estado
        self._variables[node_id] = final_val
        self._notify(node_id, final_val)

    def get_variable(self, node_id):
        if self.isVariableSet(node_id):
            return self._variables.get(node_id)
        else:
            raise KeyError(f"Variável '{node_id}' não encontrada no OpcuaDTO.")
    
    def isVariableSet(self, node_id):
        return node_id in self._variables

    def add_observer(self, callback):
        """Registra uma função callback(node_id, value) para receber atualizações."""
        if callback not in self._observers:
            self._observers.append(callback)

    def remove_observer(self, callback):
        if callback in self._observers:
            self._observers.remove(callback)

    def _notify(self, node_id, value):
        for callback in self._observers:
            try:
                callback(node_id, value)
            except Exception as e:
                print(f"Erro no observer OpcuaDTO: {e}")