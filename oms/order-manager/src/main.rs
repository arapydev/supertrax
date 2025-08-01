// Importamos los componentes necesarios para construir un servidor gRPC con Tonic.
use tonic::{transport::Server, Request, Response, Status};

// Importamos el código que 'tonic-build' generó automáticamente a partir de nuestro archivo oms.proto.
// Rust sabe dónde encontrarlo gracias a nuestro script 'build.rs'.
// 'order_manager_server' es el trait del servidor, y 'OrderManager' es el nombre que le dimos.
use oms::order_manager_server::{OrderManager, OrderManagerServer};
// 'TradeRequest' y 'TradeResponse' son los mensajes que definimos en el contrato.
use oms::{TradeRequest, TradeResponse};

// Definimos un módulo 'oms' para que coincida con el nombre del paquete en nuestro .proto
// Esto es necesario para que la importación de arriba funcione.
pub mod oms {
    tonic::include_proto!("oms"); // Le dice a tonic que incluya aquí el código generado.
}

// Creamos una estructura para nuestro servicio. Será la que implemente la lógica.
#[derive(Debug, Default)]
pub struct MyOrderManager {}

// Usamos el macro 'async_trait' de tonic para poder usar 'async/await' en nuestra implementación.
#[tonic::async_trait]
impl OrderManager for MyOrderManager {
    // Implementamos la función 'send_trade_order' que definimos en el contrato.
    // Recibe una Petición (Request) que contiene un TradeRequest.
    // Devuelve un Resultado (Result) que contiene una Respuesta (Response) con un TradeResponse, o un Error de Estado (Status).
    async fn send_trade_order(
        &self,
        request: Request<TradeRequest>,
    ) -> Result<Response<TradeResponse>, Status> {
        
        // --- AQUÍ VIVIRÁ NUESTRA LÓGICA DE MVP ---

        // Imprimimos un mensaje para saber que hemos recibido una llamada.
        println!("¡Orden recibida desde el backend!");

        // Obtenemos los datos de la petición. 'into_inner()' extrae nuestro TradeRequest.
        let trade_request = request.into_inner();

        // Imprimimos los detalles de la orden para verificar que los datos llegaron correctamente.
        println!("  Instrumento: {}", trade_request.instrument);
        println!("  Lado: {}", trade_request.side);
        println!("  Volumen: {}", trade_request.volume);
        println!("  Stop Loss: {}", trade_request.stop_loss);
        println!("  Take Profit: {}", trade_request.take_profit);

        // Creamos la respuesta que enviaremos de vuelta al backend.
        let reply = TradeResponse {
            success: true, // Confirmamos que la recibimos.
            order_id: "orden-simulada-123".into(), // Devolvemos un ID de orden falso.
            message: "Orden recibida y en procesamiento por el OMS de Rust.".into(),
        };

        // Envolvemos nuestra respuesta en el tipo 'Response' y la devolvemos.
        Ok(Response::new(reply))
    }
}

// El punto de entrada de nuestro programa. Usamos el macro de Tokio para un runtime asíncrono.
#[tokio::main]
async fn main() -> Result<(), Box<dyn std::error::Error>> {
    // Definimos la dirección y el puerto donde nuestro servidor escuchará.
    let addr = "[::1]:50051".parse()?;
    // Creamos una instancia de nuestro servicio.
    let order_manager = MyOrderManager::default();

    println!("Servidor OMS escuchando en {}", addr);

    // Construimos y arrancamos el servidor.
    Server::builder()
        .add_service(OrderManagerServer::new(order_manager))
        .serve(addr)
        .await?;

    Ok(())
}