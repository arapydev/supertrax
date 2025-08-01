fn main() -> Result<(), Box<dyn std::error::Error>> {
    tonic_build::configure()
        .compile(
            &["proto/oms.proto"], // La ruta ahora es local
            &["proto"],          // El directorio de búsqueda también es local
        )?;
    Ok(())
}