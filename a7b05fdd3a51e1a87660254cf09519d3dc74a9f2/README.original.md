# Aspose.PSD FOSS Java

[![Maven Central](https://maven-badges.herokuapp.com/maven-central/org.aspose.psd/aspose-psd-foss-java/badge.svg)](https://maven-badges.herokuapp.com/maven-central/org.aspose.psd/aspose-psd-foss-java)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](https://opensource.org/licenses/MIT)

FOSS implementation of Aspose.PSD for Java - A high-performance API for working with PSD and PSB files.

## Getting started

This project is a FOSS (Free and Open Source Software) implementation of Aspose.PSD for Java, providing a high-performance API for working with PSD and PSB files.

### Prerequisites

- Java 11 or higher
- Maven 3.6 or higher

## Installation

### Maven

Add the following dependency to your `pom.xml`:

```xml
<dependency>
    <groupId>org.aspose.psd</groupId>
    <artifactId>aspose-psd-foss-java</artifactId>
    <version>1.0.0</version>
</dependency>
```

## Quick Start

Below is a simple example of how to load a PSD file, inspect its layers, and save it back preserving all original data.

```java
import org.aspose.psd.ImageLoadOptions;
import org.aspose.psd.PsdImage;
import org.aspose.psd.layers.Layer;

public class QuickStart {
    public static void main(String[] args) throws Exception {
        // Load a PSD document
        try (PsdImage psd = (PsdImage) PsdImage.load("sample.psd")) {
            System.out.println("Width: " + psd.getWidth());
            System.out.println("Height: " + psd.getHeight());
            System.out.println("Number of layers: " + psd.getLayers().size());

            // Iterate through layers and print basic info
            for (Layer layer : psd.getLayers()) {
                System.out.println("Layer: " + layer.getName() + ", Visible: " + layer.isVisible());
            }

            // Modify a layer property (e.g., set opacity to 50%)
            if (!psd.getLayers().isEmpty()) {
                Layer first = psd.getLayers().get(0);
                first.setOpacity(128); // 0-255 range, 128 ≈ 50%
            }

            // Save the PSD document – this will preserve all untouched sections byte‑exactly
            psd.save("sample_modified.psd");
        }
    }
}
```

This example demonstrates loading, basic inspection, a simple modification, and saving. The library preserves all unmodified sections, ensuring a byte‑exact round‑trip.

## Documentation & Resources

* **[API Reference (Javadoc)](https://javadoc.io/doc/org.aspose.psd/aspose-psd-foss-java/latest/index.html)** – Detailed Javadoc for all public classes and methods.
* **[Getting Started Guide](https://products.aspose.org/psd/java/)** – Overview of loading, inspection and saving in Java.
* **[Knowledge Base](https://kb.aspose.org/psd/java/)** – FAQs, troubleshooting and how‑to articles.
* **[GitHub Repository](https://github.com/aspose-psd-foss/Aspose.PSD-FOSS-for-Java)** – Source code, issue tracker and contribution guide.

## Scope and Limitations

* **Supported formats** – Adobe Photoshop `.psd` (up to 30 000 px) and `.psb` (up to 300 000 px) containers are fully supported.
* **No pixel rendering** – The library provides structural access and metadata; rasterization of pixel data is not included.
* **Read‑only mask and blending‑range data** – Modifying mask data or blending ranges is currently not supported.
* **Color mode support** – Indexed palette, RGB and CMYK payloads are parsed; other modes are preserved as raw data.
* **Compression** – RAW, RLE and ZIP (with/without prediction) image data structures are supported.

## Development and Testing

To build and run the test suite locally:

```bash
# Clone the repository (if not already done)
git clone https://github.com/aspose-psd-foss/Aspose.PSD-FOSS-for-Java.git
cd Aspose.PSD-FOSS-for-Java

# Build the project and run tests
mvn clean verify
```

The test suite includes unit tests for header parsing, color data, image data structures, layer handling, resource parsing, and byte‑exact round‑trip verification.
## Building from source

### Clone the repository

```bash
 git clone https://github.com/aspose-psd-foss/Aspose.PSD-FOSS-for-Java.git
 cd Aspose.PSD-FOSS-for-Java
```

### Build the project

```bash
mvn clean install
```

### Build Javadoc

```bash
mvn javadoc:javadoc
```

## Contributing

We welcome contributions! Please follow these steps:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add some amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## License

This project is licensed under the MIT License.

## Contact

 - Project URL: [https://github.com/aspose-psd-foss/Aspose.PSD-FOSS-for-Java](https://github.com/aspose-psd-foss/Aspose.PSD-FOSS-for-Java)
- Email: psd@aspose.com
