# Judge Backgrounds & Evaluation Preferences Research

## 1. Google Developer Advocates Who Judge Hackathons

### Key Figures
- **Code-y Webber** - Developer Advocate at Google DeepMind, served as judge for the Gemini 3 Hackathon
- **Stephanie Wong** - Google Cloud Developer Advocate, conducted interviews with hackathon winners at "House of Kube" events and on theCUBE broadcasts
- Google I/O Gemini presenters frequently rotate into judging roles for Gemini-related hackathons

### Developer Advocate Mindset
- DAs are evaluated on **developer adoption and ecosystem growth**, so they favor projects that showcase Google technology in compelling, reproducible ways
- They value projects that could become **reference implementations** or **case studies** they can feature in talks
- They look for **creative, unexpected uses** of Google APIs that demonstrate platform capabilities beyond obvious use cases
- They appreciate projects that show deep understanding of the platform, not just surface-level API calls

### What Google Developer Advocates Publicly Praise
- Strong and interesting UI that stands out visually
- Production-readiness over prototype-level demos
- Clear communication of technical architecture
- Projects that could inspire other developers
- Accessibility-focused applications (multiple Gemini API competition winners addressed accessibility)

---

## 2. Previous Google Hackathon Judging Patterns

### Projects That Scored Highest

**Gemini API Developer Competition 2024 Winners:**
| Project | Why It Won |
|---------|-----------|
| **Jayu** | AI assistant integrating across web browsers, code editors, music, games - showed breadth of multimodal capability |
| **Vite Vere** | Assists people with cognitive disabilities - deep accessibility focus + Gemini visual understanding |
| **Gaze Link** (Best Android) | Eye-tracking communication for ALS patients - genuine human impact + technical innovation |
| **ViddyScribe** | Auto audio descriptions for videos - accessibility + practical utility |
| **Outdraw** | Game where humans try to stump AI - creative/fun application showing AI versatility |
| **Prospera** | Real-time AI sales coach - practical business application + multimodal analysis |
| **Pen Apple** | Deck builder game using Gemini Flash - creative gaming application |

**Key Pattern:** Accessibility and human impact dominated winners. 4 of 7 winners directly addressed disability/accessibility.

**GKE Hackathon Winners:**
- **Cart-to-Kitchen AI Assistant** (Grand Prize) - Analyzed grocery carts, recommended recipes using Gemini + GKE Autopilot + ADK + A2A protocols
- Winners demonstrated **multi-service integration** across Google Cloud products

**ADK Hackathon Winners:**
- 476 submissions, 10,432 participants
- Winners focused on **multi-agent orchestration** and real enterprise use cases
- Projects using SequentialAgent and ParallelAgent patterns scored well

**ODSC-Google Cloud Hackathon 2025:**
- **1st Place: Medical AI System** by Jeremy Samuel - Multi-agent AI for medical diagnosis using ADK with specialist agents
- Strategy: Started with core text-based diagnosis, then expanded to multi-agent + multimodal
- **Key insight:** Iterative development approach praised (MVP first, then scale complexity)

**BigQuery AI Hackathon:**
- **TriLink** won with multimodal analysis of text + images for home security ticket handling
- Automated triage showing practical enterprise value

**Google Cloud Gen AI Hackathon 2025:**
- 270,000 developers participated
- Trend: Shift from prototype-style demos toward **agentic systems and explainable models built for enterprise integration**
- Domain-specific, production-ready tooling scored highest
- Solutions that plug into existing enterprise pipelines with auditability and scalability

### Common Themes Across All Winners
1. **Real-world problem solving** - Not toy demos but genuine pain points
2. **Accessibility and inclusion** - Disproportionately rewarded
3. **Multimodal capabilities** - Using vision + audio + text together
4. **Multi-service Google integration** - Using multiple Google Cloud products together
5. **Production-readiness** - Clean architecture, deployment-ready code
6. **Iterative approach** - Start simple, scale up complexity

---

## 3. Deep Analysis of Judging Criteria

### Innovation & Multimodal UX (40% weight)

**What "Breaking the Text Box Paradigm" Means:**
- Move beyond a simple text input/output chatbot interface
- Create agents that process and respond across **multiple modalities simultaneously**: vision, audio, text, and action
- The agent should "See, Hear, and Speak" fluidly - not just one at a time
- Experience should be **live and context-aware**, not disjointed and sequential
- The agent should have a **distinct personality/voice**

**Specific Sub-criteria:**
- Does the project break the "text box" paradigm?
- Does the agent help "See, Hear, and Speak" fluidly?
- Does it have a distinct personality/voice?
- Is the experience "Live" and context-aware or disjointed and sequential?

**What Impresses Judges:**
- Real-time multimodal interaction (processing camera feed + audio + responding with speech simultaneously)
- Context persistence across modalities (remembering what was seen when responding to voice)
- Natural, conversational flow rather than command-response patterns
- Creative input methods beyond typing (gestures, gaze, voice, camera)

**Examples of "Breaking the Text Box":**
- Robot control: Looking at camera feed + hearing instructions + executing physical actions
- Medical diagnosis: Analyzing scans + listening to doctor notes + providing spoken diagnosis (28.4% faster)
- Manufacturing QA: Camera vision + microphone + force sensors simultaneously
- UI navigation: Observing browser/device display and executing actions per user intent
- Creative storytelling: Weaving text, images, audio, and video into a single flow

**What Does NOT Impress:**
- Text-only chatbots with a nice UI skin
- Single-modality projects that only use one Gemini capability
- Sequential modality use (upload image -> get text response -> no further interaction)
- Projects that could work just as well without multimodal features

### Technical Implementation & Agent Architecture (30% weight)

**What Demonstrates Excellent Google Cloud/ADK Usage:**

**Required Technical Elements:**
- Effective use of Google GenAI SDK or ADK
- Backend robustly hosted on Google Cloud
- Sound agent logic
- Graceful error handling
- Evidence of grounding (avoiding hallucinations)

**Multi-Agent Architecture Patterns (from ADK best practices):**
- **LLM Agents**: Leverage Gemini for natural language understanding and reasoning
- **Workflow Agents**: Orchestrate task execution (SequentialAgent, ParallelAgent)
- **Custom Agents**: Specific business logic
- **Orchestrator Agent**: Command center with explicit planning logic, transparent delegation, context-aware decisions

**Communication Patterns:**
- **Shared Session State**: Agents write/read from shared context (digital whiteboard)
- **LLM-Driven Delegation**: Parent agent dynamically routes to best sub-agent

**What Scores High:**
- Using multiple Google Cloud services together (Gemini + Cloud Run + BigQuery + etc.)
- Clean, well-documented code architecture
- Proper agent-to-agent communication patterns
- Real grounding strategies (RAG, tool use, function calling)
- Security considerations (OWASP integration with callbacks)
- Production-quality error handling and logging
- Clear separation of concerns between agents

**What Scores Low:**
- Simple single-agent with one API call
- No error handling or edge case consideration
- Code that only works in demo conditions
- Not actually using Google Cloud for hosting/services
- Hallucination-prone responses without grounding

### Demo & Presentation (30% weight)

**What Makes a Winning Demo Video:**

**Required Elements:**
- Video clearly defines the problem and solution
- Architecture diagram is clear
- Visual proof of Cloud deployment (console logs or GCP service links)
- Shows the software actually working (no mockups)
- Under 4 minutes

**What Judges Evaluate:**
- Does the video clearly define the problem and solution?
- Is the architecture diagram clear?
- Is there visual proof of Cloud deployment?
- Does the video show the software actually working?

---

## 4. Bonus Point Optimization

### Content Publication (+0.6 potential bonus)

**Note:** The specific +0.6 bonus for content publication was not confirmed in the official Gemini Live Agent Challenge rules found online. However, based on Google's broader ecosystem values:

**What Kind of Content is Most Impactful:**
- **Blog posts/articles** about your project on Medium, Dev.to, or personal blog
- **Tutorial-style content** showing how you built the project (Google values knowledge sharing)
- **Video content** on YouTube explaining the architecture
- **Open-source contribution** with well-documented README

**Google Developer Expert Program Values:**
- Knowledge sharing and consistent content creation
- YouTube tutorials, blog posts, open-source contributions
- Speaking at events (GDG events, conferences)
- Community engagement and mentoring
- Ability to articulate clearly and provide meaningful advice

**Content Strategy for Maximum Impact:**
1. Write a Medium article (tagged with Google Cloud, Gemini, ADK)
2. Create a YouTube walkthrough of your project
3. Tweet/post about your project tagging @googledevs and relevant GDG accounts
4. Contribute to open-source ADK documentation or examples

### Automated Deployment (+0.2 potential bonus)

**Note:** The specific +0.2 bonus was not confirmed in official rules, but deployment quality is evaluated.

**Terraform/IaC Best Practices for Google Cloud:**
- Use Terraform with Cloud Build for automated deployment
- Infrastructure as Code with `main.tf` defining all GCP resources
- Cloud Run deployment with containerized application
- CI/CD pipeline with Cloud Build triggers on git push
- Remote state management with GCS backend

**Deployment Script Components:**
```
terraform/
  main.tf           # Core infrastructure
  variables.tf      # Configurable parameters
  outputs.tf        # Deployment URLs and endpoints
  cloud_run.tf      # Cloud Run service definition
cloudbuild.yaml     # Cloud Build CI/CD pipeline
Dockerfile          # Container definition
deploy.sh           # One-click deployment script
```

**What Demonstrates Excellence:**
- One-command deployment from scratch
- Environment variable management
- Health checks and monitoring setup
- Auto-scaling configuration
- Clean teardown script

### GDG Membership (+0.2 potential bonus)

**Note:** The specific +0.2 bonus was not confirmed in official rules.

**How to Maximize GDG Connection:**
- Join your local Google Developer Group
- Attend GDG events (many host "Build with AI" hackathons)
- GDGs on Campus provides learning opportunities for university students
- Hackathons are a core GDG activity format
- Being an active GDG member shows engagement with Google's developer ecosystem

---

## 5. Demo Video Best Practices

### Optimal Structure for a 4-Minute Demo

**Minute 0:00-0:30 - Hook & Problem Statement (30 seconds)**
- Open with a compelling statistic or personal story that illustrates the pain
- "X million people struggle with..." or "Every day, professionals waste hours..."
- Make judges feel the problem viscerally

**Minute 0:30-1:00 - Solution Overview (30 seconds)**
- One-sentence description of your solution
- Quick architecture diagram showing Gemini + GCP services
- "We built [X], an agent that sees, hears, and speaks to solve this"

**Minute 1:00-3:00 - Live Demo (2 minutes - THE MOST IMPORTANT PART)**
- Show the working software in action
- Demonstrate multimodal capabilities: voice input -> visual processing -> spoken response
- Show 2-3 key user flows
- Include at least one "wow moment" that shows something unexpected
- Show Google Cloud console briefly (proof of deployment)

**Minute 3:00-3:45 - Technical Architecture (45 seconds)**
- Architecture diagram showing agent flow
- Mention specific Google services used (Gemini, Cloud Run, ADK, etc.)
- Brief mention of multi-agent orchestration if applicable
- Show clean code structure (brief flash)

**Minute 3:45-4:00 - Impact & Future Vision (15 seconds)**
- Who benefits and how
- One line about future potential
- Strong closing statement

### Production Quality Tips

**Video Quality:**
- Use high-quality screen recording (OBS Studio, ScreenFlow)
- 1080p minimum resolution
- Clean desktop (no personal files visible)
- Full-screen application during demo
- Good lighting if showing face

**Audio Quality:**
- Use a dedicated microphone (not laptop mic)
- Record in a quiet room
- Clear, articulate narration
- Moderate pace (not too fast, not too slow)
- Add subtitles for accessibility (judges may watch without sound)

**Content Strategy:**
- Script your narration before recording
- Practice the demo flow 3+ times
- Have a backup recording if live demo fails
- Focus 60% of time on the demo, not the pitch
- Avoid "umm" and filler words

### Common Mistakes to Avoid
1. Spending too much time on problem/pitch and not enough on demo
2. Showing Figma mockups instead of working software
3. Poor audio quality that makes narration hard to follow
4. Going over the time limit
5. Not showing Google Cloud deployment proof
6. Not including an architecture diagram
7. Demonstrating only text-based interaction
8. Not demonstrating the "multimodal" aspect clearly

---

## 6. What Google Values in Developer Projects

### Google's Core Developer Values
- **"AI for Everyone"** - Democratizing AI access, not just for experts
- **Practical Impact** - Real solutions for real problems
- **Accessibility** - Making technology inclusive
- **Open Source** - Contributing to the developer community
- **Innovation** - Novel approaches that advance the field

### Google Developer Expert (GDE) Program Criteria
- Solid expertise in Google technology (Android, Cloud, ML, Web)
- Active knowledge sharing (blogs, videos, talks, mentoring)
- Community engagement and willingness to help others
- Open-source contributions
- No formal education requirement - expertise and impact matter

### What Google Highlights in Developer Case Studies
- Enterprise integration and production readiness
- Multi-service Google Cloud integration
- Scalability and auditability
- Domain-specific solutions (healthcare, education, accessibility)
- Novel UX patterns that go beyond standard chatbots

### Google's Messaging Around "AI for Everyone"
- Gemini is positioned as democratizing AI capabilities
- Focus on making AI accessible to non-technical users
- Emphasis on responsible AI with grounding and safety
- Multi-agent systems as the future of enterprise AI
- "See, Hear, Speak" as the new paradigm (replacing text-only interfaces)

---

## 7. Strategic Recommendations for Winning

### High-Impact Strategies Based on Research

1. **Choose an accessibility/social impact problem** - Disproportionately rewarded across all Google hackathons
2. **Build genuine multimodal interaction** - Voice + vision + text simultaneously, not sequentially
3. **Use multiple Google Cloud services** - Gemini + ADK + Cloud Run + at least one more service
4. **Implement multi-agent architecture** - Orchestrator + specialist agents using ADK patterns
5. **Make the demo the star** - 60% of video time on working software
6. **Include architecture diagram** - Required and heavily evaluated
7. **Show Google Cloud console** - Proof of deployment is mandatory
8. **Tell a human story** - Start with a real person's real problem
9. **Build one feature perfectly** - Better than five half-baked features
10. **Start submission early** - Submit 2+ days before deadline to polish

### The "Wow Factor" Formula
Based on analysis of all winners:
- **Unexpected application** of familiar technology (like using Gemini for eye-tracking communication)
- **Real-time multimodal processing** that feels magical
- **Genuine human impact** that makes judges feel something
- **Clean, polished UX** that shows care and attention
- **Technical depth** visible in architecture without being overwhelming

### Red Flags That Lose Points
- Pure text chatbot with no multimodal features
- No working demo (only slides/mockups)
- Generic "AI assistant" without specific domain focus
- Poor audio/video quality in submission
- Missing required deliverables (architecture diagram, deployment proof)
- Going over the 4-minute video limit
- Not using required technologies (Gemini, GenAI SDK/ADK, Google Cloud)

---

## Sources

- [Gemini Live Agent Challenge](https://algo-mania.com/en/blog/hackathons-coding/gemini-live-agent-challenge-create-immersive-ai-agents-with-google-gemini-live/)
- [Gemini API Developer Competition Winners](https://developers.googleblog.com/en/announcing-the-winners-of-the-gemini-api-developer-competition/)
- [GKE Hackathon Winners](https://cloud.google.com/blog/topics/developers-practitioners/winners-and-highlights-from-gke-hackathon)
- [ADK Hackathon Results](https://cloud.google.com/blog/products/ai-machine-learning/adk-hackathon-results-winners-and-highlights)
- [ODSC-Google Cloud Hackathon Insights](https://odsc.medium.com/insights-from-the-winners-of-the-2025-odsc-google-cloud-hackathon-b5bd4f40091d)
- [Google Cloud Gen AI Hackathon 2025](https://www.outlookbusiness.com/artificial-intelligence/google-cloud-gen-ai-hackathon-2025-winners-use-cases-and-what-270000-developers-built)
- [Hackathon Judging Criteria](https://praveenax.medium.com/what-are-the-criteria-to-judge-as-a-hackathon-jury-32e08046dd4b)
- [Devpost Winning Tips](https://medium.com/developer-circles-lusaka/tips-on-how-to-win-an-online-hackathon-on-devpost-c548027e0eae)
- [Hackathon Demo Tips - TechCrunch](https://techcrunch.com/2014/09/01/how-to-crush-your-hackathon-demo/)
- [Hackathon Demo Video Guide](https://tips.hackathon.com/article/creating-the-best-demo-video-for-a-hackathon-what-to-know)
- [Google Developer Expert Program](https://developers.google.com/community/experts)
- [ADK Documentation](https://google.github.io/adk-docs/)
- [Building Multi-Agent Systems with ADK](https://cloud.google.com/blog/topics/developers-practitioners/building-collaborative-ai-a-developers-guide-to-multi-agent-systems-with-adk)
- [Gemini 3 Hackathon](https://www.competehub.dev/en/competitions/devpost27555)
- [Hackathon Presentation Tips](https://medium.com/upstate-interactive/8-tips-to-a-successful-hackathon-demo-and-presentation-4d1ae83415ad)
- [Multimodal Agents in Generative AI](https://brics-econ.org/multimodal-agents-in-generative-ai-tools-that-see-hear-and-act)
