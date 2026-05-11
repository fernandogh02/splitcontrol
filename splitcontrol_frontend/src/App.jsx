import { useEffect, useState } from 'react';
import axios from 'axios';

function App() {
  const [mensaje, setMensaje] = useState('');

  useEffect(() => {
    axios.get('http://127.0.0.1:8000/api/prueba/')
      .then((response) => {
        setMensaje(response.data.mensaje);
      })
      .catch((error) => {
        console.error('Error al conectar con la API:', error);
        setMensaje('No se pudo conectar con la API.');
      });
  }, []);

  return (
    <div className="container mt-5">
      <div className="card shadow">
        <div className="card-body">
          <h1 className="text-center">SplitControl</h1>
          <p className="text-center">
            Prueba de conexión entre React y Django REST Framework.
          </p>
          <div className="alert alert-info text-center">
            {mensaje}
          </div>
        </div>
      </div>
    </div>
  );
}

export default App;