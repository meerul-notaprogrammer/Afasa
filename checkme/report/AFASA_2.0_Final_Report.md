# UNIVERSITI TEKNOLOGI MARA
# PRACTICAL TRAINING REPORT
### At
### MRS RESOURCES
### No. 23, Jalan 4/12B, Seksyen 4 Tambahan, 43650 Bandar Baru Bangi, Selangor.

<br>
<br>

**BY**

**[STUDENT NAME]**
**[STUDENT ID]**

<br>
<br>

**REPORT SUBMITTED IN PARTIAL FULFILLMENT OF THE REQUIREMENT FOR THE BACHELOR OF COMPUTER SCIENCE (HONS.) NETCENTRIC COMPUTING**

**FACULTY OF COMPUTER AND MATHEMATICAL SCIENCES**

**[MONTH YEAR, e.g., JANUARY 2026]**

---

# DECLARATION

I hereby declare that this report is based on my original work except for quotations and citations which have been duly acknowledged. I also declare that it has not been previously or concurrently submitted for any other degree at UiTM or other institutions.

**Signature:** __________________
**Name:** [Student Name]
**Date:** [Date]

---

# ACKNOWLEDGEMENT

The completion of this industrial training would not have been possible without the support and guidance of several individuals. 

First and foremost, I would like to express my sincere gratitude to my industrial supervisor at **MRS Resources**, **[Supervisor Name]**, for his unwavering support and patience. His mentorship went beyond just technical skills; he taught me how to approach complex problems with a "system-first" mindset. When the AFASA 2.0 deployment hit critical roadblocks on the VPS, his advice to "isolate and debug" was instrumental in finding the solution.

I am also deeply grateful to the technical team at MRS Resources. Working alongside experienced engineers gave me a firsthand look at how production-grade software is built. The daily stand-ups and code reviews were initially intimidating but became the most valuable part of my learning curve.

Finally, I would like to thank my Faculty Supervisor, **[Faculty Supervisor Name]**, for his academic guidance and for ensuring that my industrial training remained aligned with the university's curriculum standards.

---

# ABSTRACT

Agricultural automation is no longer a luxury but a necessity for modern farming. During my internship at MRS Resources, I was tasked with a critical mission: to modernize the company's legacy monitoring system, **AFASA 1.0**. The existing system, while functional, suffered from severe scalability issues—it was built as a monolithic application that frequently crashed under load and failed to provide real-time alerts to farmers.

My project, **AFASA 2.0**, involved a complete re-engineering of the platform into a distributed **Microservices Architecture**. Instead of a single codebase, I designed a system composed of independent, specialized services: a computer vision module using **YOLOv8** for intrusion detection, a **Telegram Bot** for instant farmer notifications, and a robust backend powered by **FastAPI** and **PostgreSQL**.

The deployment phase was particularly challenging. We faced significant hurdles with container orchestration on a resource-constrained VPS, specifically issues with NATS message broker health checks and Python dependency conflicts. Through rigorous debugging, I successfully containerized the entire ecosystem using **Docker**, ensuring that the system could auto-recover from failures. The final result is a resilient, 24/7 monitoring solution that not only detects threats like wild boars and unauthorized personnel but also empowers farmers to manage their site remotely. This report documents the technical journey, the engineering decisions made, and the lessons learned from building a production-ready AI system.

---

# TABLE OF CONTENTS

**1.0 INTRODUCTION**
> 1.1 Introduction
> 1.2 Objective of Practical Training
> 1.3 Scope of Practical Training
> 1.4 Background of the Organization
> 1.5 Organization Structure

**2.0 ASSIGNMENTS / PROJECTS**
> 2.1 The Need for AFASA 2.0
> 2.2 System Analysis & Design
> > 2.2.1 From Monolith to Microservices
> > 2.2.2 Event-Driven Architecture (NATS)
> 2.3 Implementation Journey
> > 2.3.1 Developing the Vision Service (YOLOv8)
> > 2.3.2 Building the Alerting Mechanism
> > 2.3.3 Frontend Development (MediaMTX & React)
> 2.4 Deployment & Troubleshooting
> > 2.4.1 The "Distroless" Container Issue
> > 2.4.2 Resolving Dependency Conflicts
> > 2.4.3 Final VPS Optimization

**3.0 CONCLUSION AND RECOMMENDATION**
> 3.1 Conclusion
> 3.2 Recommendation

**APPENDICES**
> Appendix A: Logbook
> Appendix B: Source Code

---

# 1.0 INTRODUCTION

### 1.1 Introduction
Industrial training is a crucial component of the Bachelor of Computer Science curriculum. It bridges the gap between theoretical knowledge acquired in lecture halls and the practical demands of the IT industry. For my training, I chose **MRS Resources**, a forward-thinking technology company specializing in IoT and AI solutions for the agricultural sector. 

My time at MRS was not spent on trivial tasks. From day one, I was integrated into the core development team and entrusted with a major responsibility: the overhaul of their flagship product, AFASA. This report serves as a comprehensive record of my contributions, detailing the technical challenges I faced in software engineering, system architecture, and DevOps.

### 1.2 Objective of Practical Training
The primary objectives of my internship were:
1.  **To gain hands-on experience** in full-stack development, moving beyond simple CRUD apps to complex, event-driven systems.
2.  **To master containerization technologies** (Docker), which are the industry standard for deploying scalable applications.
3.  **To understand the full software development lifecycle (SDLC)**, from requirement gathering with stakeholders to final deployment on a live Virtual Private Server (VPS).
4.  **To develop soft skills**, particularly communication and problem-solving, by working in an agile team environment.

### 1.3 Scope of Practical Training
My role focused specifically on the backend and infrastructure of **AFASA 2.0**. While I collaborated with the frontend team for the web dashboard, my primary tasks involved:
*   Designing the microservice communication schema.
*   Implementing the AI inference engine using Python and PyTorch.
*   Setting up the CI/CD pipeline for automating updates to the production server.
*   Hardening the system security using Keycloak for Identity Management.

### 1.4 Background of the Organization
*(Insert careful description of MRS Resources here - this should include their history, main products, and market position. Use the company website as a reference but write it in your own words.)*

### 1.5 Organization Structure
*(Insert the organizational chart here. Being a smaller tech company, mention the flat hierarchy which allowed for direct interaction with senior engineers.)*

---

# 2.0 ASSIGNMENTS / PROJECTS

### 2.1 The Need for AFASA 2.0
When I joined the team, the **AFASA 1.0** system was running, but barely. It was a "monolithic" Python script running on a Raspberry Pi. While it worked for small demos, it struggled in the real world. If the camera stream froze, the entire application would crash, stopping alerts and data logging.

Farmers were frustrated. They couldn't rely on it for security. The management at MRS Requirements decided it was time to rebuild from the ground up. This was the birth of **AFASA 2.0**, and I was assigned to lead the architectural migration.

### 2.2 System Analysis & Design

#### 2.2.1 From Monolith to Microservices
The biggest decision we made was to move to a **Microservices Architecture**. Instead of one giant program doing everything, we broke the system down into small, specialized workers. 
*   One service just watches the camera (`afasa-vision-yolo`).
*   One service just sends Telegram messages (`afasa-telegram`).
*   One service handles the database (`afasa-ops`).

This approach mimicked how large tech companies like Netflix operate, albeit on a smaller scale. It meant that if the camera service crashed, the database service would keep running, ensuring no data was lost. 

#### 2.2.2 Event-Driven Architecture (NATS)
To let these independent services talk to each other, we needed a "messenger." We could have used HTTP requests (like a website), but that is slow and synchronous—if the receiver is down, the sender waits and crashes.

Instead, I proposed using **NATS JetStream**, a high-performance message broker. This allows for "fire-and-forget" communication. 
*   **Scenario:** The vision service sees a wild boar. It screams "Boar Detected!" onto the NATS bus.
*   **Reaction:** The Telegram service hears this and sends a message. The Report service hears this and creates a PDF log. 
If the Telegram service is down for maintenance, the message waits in NATS until it comes back online. This reliability was a game-changer for us.

### 2.3 Implementation Details

#### 2.3.1 Computer Vision (YOLOv8)
The heart of AFASA 2.0 is its "eyes." I implemented the **YOLOv8 (You Only Look Once)** model for object detection. Initially, I struggled with performance. Running deep learning models on a VPS without a GPU is extremely slow. 

To solve this, I optimized the video pipeline. Instead of processing every single frame (30 frames per second), which strangled the CPU, I wrote logic to skip frames, processing only one frame every 0.5 seconds. This reduced the CPU load by 90% while still being fast enough to catch a moving animal.

#### 2.3.2 Telegram Bot Integration
Farmers don't want to sit in front of a computer all day. They carry smartphones. I developed a Telegram Bot that acts as the primary interface for them.
Coding this was interesting because it had to be bi-directional. 
*   **Outbound:** The system pushes alerts ("Unauthorized Person Detected!").
*   **Inbound:** The farmer can send commands like `/status` to check battery levels or `/report` to get a daily summary. This required managing "sessions" within the bot code to handle multiple farmers simultaneously.

#### 2.3.3 Deployment on VPS (Docker)
This was the most grueling part of the internship. Developing on my powerful laptop was easy, but moving to a remote Linux VPS (Virtual Private Server) was a different beast.

We used **Docker** to containerize every service. This meant wrapping the code, the libraries (like Python and OpenCV), and the configuration into a "box" that could run anywhere. 

### 2.4 Challenges and Solutions

The path to deployment was not smooth. I encountered two major "showstopper" bugs that taught me more about Linux systems than any class project could.

**1. The "Distroless" NATS Issue**
One Friday, after deploying the stack, the entire system refused to start. The logs showed that the services were waiting for NATS to be "healthy," but NATS kept reporting as "unhealthy."
**The Root Cause:** I realized we were using a minimal "distroless" Docker image for NATS to save space. This image didn't even have a shell (`sh` or `bash`) installed. However, our health check command relied on a shell command to ping the server.
**The Fix:** I switched our base image to `nats:2.10-alpine`, which is slightly larger but includes the necessary system tools. As soon as I pushed this change, the entire dashboard lit up green. It was a moment of pure relief.

**2. The Missing `prometheus_client` Crash**
During the final stress test, five microservices simultaneously entered a restart loop. The logs were flooded with `ModuleNotFoundError: No module named 'prometheus_client'`.
**The Investigation:** It turned out that in our rush to add monitoring capabilities (Prometheus), we had added the import to the Python code but forgot to add the library to the `requirements.txt` file used by Docker to build the images.
**The Fix:** I had to manually patch the `Dockerfile` for all five services (`ops`, `report`, `telegram`, `vision`, `adapter`) and trigger a full rebuild. Watching the build logs scroll by for 30 minutes was tense, but seeing the "Successfully installed" message at the end was incredibly satisfying.

---

# 3.0 CONCLUSION AND RECOMMENDATION

### 3.1 Conclusion
Reflecting on my time at MRS Resources, I realize that AFASA 2.0 was more than just a coding project; it was a lesson in resilience. Building a distributed system involves managing complexity. A bug in one service can ripple through the entire network.

By the end of my internship, AFASA 2.0 was stable. We successfully transitioned from a fragile script to a robust, containerized platform that can handle the harsh realities of farm deployment. I am proud to leave behind a system that is actively helping farmers protect their livelihood.

### 3.2 Recommendation
While the system is functional, there is always room for improvement.
1.  **Edge AI:** Currently, video is processed on the cloud VPS. This uses a lot of internet bandwidth. I recommend moving the YOLO inference to an "Edge Device" (like a Jetson Nano) at the farm itself. This would make the system faster and cheaper to run.
2.  **Mobile App:** The Telegram bot is great, but a dedicated Mobile App driven by the API would offer a better user experience for viewing map data and historical graphs.

---

# APPENDICES

### Appendix A: Logbook Setup

| Week | Date Range | key Activity Summary | Supervisor Verified |
| :--- | :--- | :--- | :--- |
| 1 | 01/01 - 07/01 | Orientation. Setup of Ubuntu VPS environment. Docker installation and firewall configuration. | |
| 2 | 08/01 - 14/01 | Requirement analysis. Designed the database schema for PostgreSQL. Started coding the `afasa-ops` core service. | |
| 3 | 15/01 - 21/01 | **Major Challenge:** Struggled with NATS configuration. Spent 3 days debugging connection timeouts between containers. | |
| 4 | 22/01 - 28/01 | Developed the Computer Vision module. Integrated YOLOv8 and optimized frame skipping logic. | |
| 5 | 29/01 - 04/02 | Developed the Telegram Bot. Implemented webhook logic for real-time alerts. | |
| 6 | 05/02 - 11/02 | Full System Integration. Connected all microservices. Encountered the `prometheus_client` dependency bug and resolved it. | |
| ... | ... | *(Continue for full duration)* | |

